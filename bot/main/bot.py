# -*- coding: utf-8 -*-
import datetime
import logging
import re
import discord
import yaml
from pathlib import Path

from main import commands
from main import database
from main.settings import Settings

class Bot(object):    
    def __init__(self, logger=None, **options):
        self.logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        command_prefix = Settings.app_defaults("cmd_prefix")
        description = Settings.app_defaults("description")
        self.client = discord.ext.commands.Bot(command_prefix=command_prefix, description=description, **options)

    def run(self):
        database.setup()
        self.set_events()
        self.set_commands()
        self.client.run(Settings.config["env"]["client_token"], reconnect=True)

    def event_ready(self):
        async def on_ready():
            prefix = Settings.app_defaults("cmd_prefix")
            self.logger.info(f"{self.client.user.name} (ID: {self.client.user.id}) is now online.")
            status = Settings.app_defaults("status").format(prefix=prefix)
            await self.client.change_presence(activity=discord.Game(name=status))

        return on_ready

    def event_message(self):
        async def on_message(message):
            async def check_content(message, check, custom_message):
                if check:
                    content = message.clean_content
                    try:
                        await message.delete()
                    except (discord.Forbidden, discord.HTTPException) as e:
                        self.logger.warning(f"Unable to delete message at {message.jump_url}. {e}")
                    else:
                        await self.say(message.author, f"{custom_message}\nYour message: ```{content}```")
                        return True

                return False

            user = message.author
            if message.guild:
                self.logger.info(f"({message.guild.name} - {message.channel.name}) {user.name}: {message.content}")
            else:
                try:
                    self.logger.info(f"({message.channel.name}) {user.name}: {message.content}")
                except AttributeError:
                    self.logger.info(f"({user.name}) {message.content}")
                finally:
                    return

            mee6_level_up = Settings.on_message_features(message.guild.id, "mee6_level_up")
            if mee6_level_up and mee6_level_up.get("enabled") and user.id == mee6_level_up["bot_id"]:
                result = re.compile(r"{}".format(mee6_level_up["message_pattern"])).search(message.content)
                if result:
                    mentioned = message.mentions[0]
                    level = int(result.group(1))
                    self.logger.info(f"{mentioned.name} reached level {level}")

                    roles = mee6_level_up["roles"]
                    for r in roles:
                        if level >= r:
                            role = discord.utils.get(message.guild.roles, id=roles[r]["id"])
                            await mentioned.add_roles(role, reason=f"User reached level {r}")
            
            pics_only = Settings.on_message_features(message.guild.id, "pics_only")
            if pics_only and pics_only.get("enabled"):
                guild = message.guild
                channel = message.channel

                if channel.id in pics_only["channels"]:
                    if await check_content(
                        message,
                        not message.attachments,
                        pics_only["channels"][channel.id]["message"]
                    ):
                        return

            await self.client.process_commands(message)

        return on_message

    def event_edit(self):
        async def on_message_edit(before, after):
            def log_message(message, content):
                if message.guild:
                    self.logger.info(f"({message.guild.name} - {message.channel.name}){content}")
                else:
                    try:
                        self.logger.info(f"({message.channel.name}){content}")
                    except AttributeError:
                        self.logger.info(f"({message.author.name}){content}")

            if before.pinned and not after.pinned:
                log_message(after, f"<Unpinned> {after.author.display_name}: {after.content}")
            elif not before.pinned and after.pinned:
                log_message(after, f"<Pinned> {after.author.display_name}: {after.content}")

            if before.content != after.content:
                log_message(after, f"<Old message> {after.author.display_name}: {before.content}")
                log_message(after, f"<Edited> {after.author.display_name}: {after.content}")

        return on_message_edit
    
    def event_member_update(self):
        async def on_member_update(before, after):
            milestones = Settings.on_member_update_features(after.guild.id, "role_message")
            if not milestones or not milestones.get("enabled"):
                return

            before_roles = [r.id for r in before.roles]
            after_roles = [r.id for r in after.roles]
            for role in milestones["roles"]:
                if role in after_roles and role not in before_roles:
                    output_channel = discord.utils.get(after.guild.channels, name=milestones[role]["channel"])
                    await self.say(output_channel, milestones["roles"][role]["message"], context=after, parse=True)
            
            return
        
        return on_member_update

    async def say(self, channel, message, context=None, parse=False):
        if parse and context:
            server_name = "the server"
            if hasattr(context, "guild"):
                server = context.guild.name

            channel_name = ""
            if hasattr(context, "channel"):
                channel = context.channel.name
            
            mention = ""
            if hasattr(context, "mention"):
                mention = context.mention

            message = message.format(server=server_name, channel=channel_name, mention=mention)
            try:
                re_channels = set(re.findall(r"\[#(.+?)\]", message))
                for c in re_channels:
                    c_object = discord.utils.get(context.guild.channels, name=c)
                    if c_object:
                        message = message.replace(f"[#{c}]", c_object.mention)
            except AttributeError:
                pass

        await channel.send(content=message)
    
    def set_commands(self, *cmds):
        self.client.add_cog(commands.Admin(self))
        self.client.add_cog(commands.General(self))
        self.client.add_cog(commands.Statistics(self))

        for c in cmds:
            self.client.add_cog(c)
        
    def set_events(self, *events):
        self.client.event(self.event_ready())
        self.client.event(self.event_message())
        self.client.event(self.event_edit())
        self.client.event(self.event_member_update())

        for e in events:
            self.client.event(e)
