# -*- coding: utf-8 -*-
import datetime
import logging
import re
import discord
import yaml
from pathlib import Path

from main import commands
from main import utils
#from main import database
from main.logger import Logger
from main.settings import Settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Bot(discord.ext.commands.Bot):
    def run(self):
        #database.setup()

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
        Logger.info(logger, f"{self.user.name} (ID: {self.user.id}) is now online.")

    async def on_message(self, message):
        async def check_content(message, check, custom_message):
            if check:
                content = message.clean_content
                try:
                    await message.delete()
                except (discord.Forbidden, discord.HTTPException) as e:
                    Logger.warn(logger, f"Unable to delete message at {message.jump_url}. {e}")
                else:
                    await utils.say(message.author, context=message, parse=True, content=f"{custom_message}\nYour message: ```{content}```")
                    return True

            return False

        user = message.author
        if message.guild:
            Logger.info(logger, f"({message.guild.name} - {message.channel.name}) {user.name}: {message.content}")
        else:
            try:
                Logger.info(logger, f"({message.channel.name}) {user.name}: {message.content}")
            except AttributeError:
                Logger.info(logger, f"({user.name}) {message.content}")
            finally:
                return

        mee6_level_up = Settings.on_message_features(message.guild.id, "mee6_level_up")
        if mee6_level_up and mee6_level_up.get("enabled") and user.id == mee6_level_up["bot_id"]:
            result = re.compile(r"{}".format(mee6_level_up["message_pattern"])).search(message.content)
            if result:
                mentioned = message.mentions[0]
                level = int(result.group(1))
                Logger.info(logger, f"{mentioned.name} reached level {level}")

                roles = mee6_level_up["roles"]
                for r in roles:
                    if level >= r:
                        role = discord.utils.get(message.guild.roles, id=roles[r]["id"])
                        await mentioned.add_roles(role, reason=f"User reached level {r}")
        
        pics_only = Settings.on_message_features(message.guild.id, "pics_only")
        if pics_only and pics_only.get("enabled"):
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
                Logger.info(logger, f"({message.guild.name} - {message.channel.name}){content}")
            else:
                try:
                    Logger.info(logger, f"({message.channel.name}){content}")
                except AttributeError:
                    Logger.info(logger, f"({message.author.name}){content}")

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
                output_channel = discord.utils.get(after.guild.channels, name=milestones["roles"][role]["channel"])
                await utils.say(output_channel, context=after, parse=True, content=milestones["roles"][role]["message"])
            
        return

    async def on_error(self, context, error):
        Logger.error(logger, error)

    async def on_command_error(self, context, error):
        cmd_name = context.command.name
        cmd_settings = Settings.command_settings(cmd_name, context.guild.id)
        if isinstance(error, discord.ext.commands.MissingPermissions) and cmd_settings.get("visible"):
            notice = "You need the following permissions for this command: {}".format(", ".join([f"`{p}`" for p in error.missing_perms]))
            await utils.say(context.channel, content=notice)
        elif isinstance(error, discord.ext.commands.NotOwner):
            return
        else:
            Logger.error(logger, error)

    def set_commands(self, *cmds):
        self.add_cog(commands.Admin(self))
        self.add_cog(commands.General(self))
        self.add_cog(commands.Statistics(self))

        for c in cmds:
            self.add_cog(c)

        for command in self.commands:
            Logger.debug(logger, f"Setting up command '{command.name}'")
            cmd_settings = Settings.command_settings(command.name)
            if not cmd_settings:
                continue

            command.aliases = cmd_settings.get("aliases", [])
            command.hidden = not cmd_settings.get("visible", True)
            command.description = cmd_settings.get("description", "")
            command.help = cmd_settings.get("help", "")
            command.usage = cmd_settings.get("usage", "")
            Logger.debug(logger, f"Command '{command.name}' all set")

    def set_events(self, *events):
        for e in events:
            self.event(e)
