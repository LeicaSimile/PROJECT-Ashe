# -*- coding: utf-8 -*-
import datetime
import logging
import re
import discord
import yaml
from pathlib import Path

from main import commands
from main import database
from main import utils
from main.settings import Settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Bot(discord.ext.commands.Bot):
    def run(self):
        database.setup()

        events = [
            self.on_ready,
            self.on_message,
            self.on_message_edit,
            self.on_member_update
        ]
        self.set_events(*events)
        self.set_commands()
        super(Bot, self).run(Settings.config["env"]["client_token"], reconnect=True)

    # --- Events ---
    async def on_ready(self):
        prefix = Settings.app_defaults("cmd_prefix")
        logger.info(f"{self.user.name} (ID: {self.user.id}) is now online.")
        status = Settings.app_defaults("status").format(prefix=prefix)
        await self.change_presence(activity=discord.Game(name=status))

    async def on_message(self, message):
        async def check_content(message, check, custom_message):
            if check:
                content = message.clean_content
                try:
                    await message.delete()
                except (discord.Forbidden, discord.HTTPException) as e:
                    logger.warning(f"Unable to delete message at {message.jump_url}. {e}")
                else:
                    await self.say(message.author, f"{custom_message}\nYour message: ```{content}```")
                    return True

            return False

        user = message.author
        if message.guild:
            logger.info(f"({message.guild.name} - {message.channel.name}) {user.name}: {message.content}")
        else:
            try:
                logger.info(f"({message.channel.name}) {user.name}: {message.content}")
            except AttributeError:
                logger.info(f"({user.name}) {message.content}")
            finally:
                return

        mee6_level_up = Settings.on_message_features(message.guild.id, "mee6_level_up")
        if mee6_level_up and mee6_level_up.get("enabled") and user.id == mee6_level_up["bot_id"]:
            result = re.compile(r"{}".format(mee6_level_up["message_pattern"])).search(message.content)
            if result:
                mentioned = message.mentions[0]
                level = int(result.group(1))
                logger.info(f"{mentioned.name} reached level {level}")

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

        await self.process_commands(message)

    async def on_message_edit(self, before, after):
        def log_message(message, content):
            if message.guild:
                logger.info(f"({message.guild.name} - {message.channel.name}){content}")
            else:
                try:
                    logger.info(f"({message.channel.name}){content}")
                except AttributeError:
                    logger.info(f"({message.author.name}){content}")

        if before.pinned and not after.pinned:
            log_message(after, f"<Unpinned> {after.author.display_name}: {after.content}")
        elif not before.pinned and after.pinned:
            log_message(after, f"<Pinned> {after.author.display_name}: {after.content}")

        if before.content != after.content:
            log_message(after, f"<Old message> {after.author.display_name}: {before.content}")
            log_message(after, f"<Edited> {after.author.display_name}: {after.content}")
    
    async def on_member_update(self, before, after):
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

    # --- Utility methods ---
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
        self.add_cog(commands.Admin(self))
        self.add_cog(commands.General(self))
        self.add_cog(commands.Statistics(self))

        for c in cmds:
            self.add_cog(c)

    def set_events(self, *events):
        for e in events:
            self.event(e)
