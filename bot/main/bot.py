# -*- coding: utf-8 -*-
import datetime
import logging
import re
import discord
import yaml
from pathlib import Path

import psycopg2
from imgurpython import ImgurClient

from main import commands
from main import database
from main import settings

class Bot(object):
    """
    Args:
        client (discord.Bot): The bot instance.
        
    """
    
    def __init__(self, logger=None, **options):
        self.logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.events_config = None
        with open(Path(__file__).parent.joinpath("config/events.yaml"), "r") as f:
            self.events_config = yaml.safe_load(f.read())

        command_prefix = ";"
        description = settings.DESCRIPTION
        self.client = discord.ext.commands.Bot(command_prefix=command_prefix, description=description, **options)

    def run(self):
        database.setup()
        self.set_events()
        self.set_commands()
        self.client.run(settings.CLIENT_TOKEN, reconnect=True)

    def event_ready(self):
        async def on_ready():
            prefix = ";"
            self.logger.info(f"{self.client.user.name} (ID: {self.client.user.id}) is now online.")
            status = f"DDR | {prefix}help for help"
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

            servers = self.events_config["servers"]
            if message.guild.id not in servers:
                return
            
            events = servers[message.guild.id].get("on_message")
            if not events:
                return

            if "level_up" in events and user.id == 159985870458322944:  # MEE6 Bot
                result = re.compile(r"<@(?:.+)>.+level ([0-9]+)").search(message.content)
                if result:
                    mentioned = message.mentions[0]
                    level = int(result.group(1))
                    self.logger.info(f"{mentioned.name} reached level {level}")

                    roles = events["level_up"]["roles"]
                    for r in roles:
                        if level >= r:
                            role = discord.utils.get(message.guild.roles, id=roles[r]["id"])
                            await mentioned.add_roles(role, reason=f"User reached level {r}")
            elif "pics_only" in events:
                guild = message.guild
                channel = message.channel

                if channel.id in events["pics_only"]:
                    if await check_content(
                        message,
                        not message.attachments,
                        events["pics_only"][channel.id]
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
            servers = self.events_config["servers"]
            if after.guild.id not in servers:
                return

            milestones = None
            try:
                milestones = servers[after.guild.id]["on_member_update"]["roles"]
            except KeyError:
                return

            before_roles = [r.id for r in before.roles]
            after_roles = [r.id for r in after.roles]
            for role in milestones:
                if role in after_roles and role not in before_roles:
                    output_channel = discord.utils.get(after.guild.channels, name=milestones[role]["channel"])
                    await self.say(output_channel, milestones[role]["message"], context=after, parse=True)
            
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
