"""Admin commands"""
import asyncio
import datetime
import logging

import discord
from discord.ext import commands
import mee6_py_api

from main import database, utils
from main.logger import Logger
from main.errors import AppError, ErrorCode
from main.settings import Settings
from main.status import CommandStatus
from . import admin_dao, admin_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN)

async def get_inactive_members(context, progress_report=True):
    """Returns a list of inactive members."""
    progress_msg = None
    included_channels = admin_dao.inactivelist_channels(context.guild)
    active_members = []
    inactive_members = []
    current_channel = None
    current_channel_index = 0
    channel_count = len(included_channels)
    channel_progress_stats = ""
    channel_count_message = ""
    current_channel_progress_message = ""

    if progress_report:
        progress_content = f"Scanning {channel_count} channels for inactive members..."
        progress_msg = await utils.say(context.channel, content=progress_content)

    async for scan in admin_utils.scan_active_members(context.guild):
        if isinstance(scan.error, discord.errors.Forbidden):
            Logger.error(logger, f"Can't access {channel.name}")
            # TODO: Edit progress_msg to indicate channel can't be accessed
        else:
            # Update channel index
            if current_channel != scan.current_channel:
                current_channel_index += 1
                current_channel = scan.current_channel
                channel_count_message = (
                    f"Scanning {current_channel_index}/{channel_count} channels for inactive members..."
                )

            update_interval = 100
            if progress_msg and not scan.current_channel_messages_scanned % update_interval:
                channel_progress_stats = (
                    f"\nMessages scanned: {scan.current_channel_messages_scanned}"
                    f"\n\nDate: {scan.message_time}"
                )

            current_channel_progress_message = (
                f"{channel_count_message}```Current channel: #{current_channel.name}{channel_progress_stats}```"
            )
            if progress_msg.content != current_channel_progress_message:
                await progress_msg.edit(content=current_channel_progress_message)

            active_members = scan.active_members

    if progress_msg:
        await progress_msg.edit(content=f"Scanned {channel_count} channels for inactive members.")

    results = [
        user for user in context.guild.members
        if user not in active_members and user.joined_at < time_boundary and not user.bot
    ]
    db_inactive_members = [] # admin_dao.inactive_members(context.guild.id)

    for member in results:
        if member.id in db_inactive_members:
            member_instance = db_inactive_members[member.id]
            member_instance.user = member
            inactive_members.append(member_instance)
        else:
            inactive_members.append(database.InactiveMember(context.guild.id, member.id, user=member))
    # update_inactive_members(context.guild.id, {m.member_id: m for m in inactive_members})

    return inactive_members

def update_inactive_members(server_id: int, after):
    """
    Args:
        server_id(int): Server's unique ID
        after(dict): Current collection of inactive members {member_id: database.InactiveMember}.

    """
    admin_dao.update_inactive_members(server_id, after)


class Admin(commands.Cog):
    """Commands usable only by the admin."""

    def __init__(self, bot):
        """
        Args:
            bot(Bot): Bot instance.

        """
        self.bot = bot

    # --- Helper functions ---
    async def inactivity_notification_invite(self, server: discord.Guild):
        """Returns an Invite object for a given server's inactivity notifications"""
        inactivity_settings = admin_dao.server_inactivity_settings(server.id)
        if not inactivity_settings:
            raise AppError(
                ErrorCode.ERR_FEATURE_NOT_FOUND,
                "'inactivity' settings not found for server ID {context.guild.id}"
            )
        elif not inactivity_settings.get("message_invite_enabled"):
            return None

        # Attach invite to message
        invite_channel = None
        invite_channel_id = inactivity_settings.get("message_invite_channel")
        if invite_channel_id:
            invite_channel = server.get_channel(invite_channel_id)

        if not invite_channel:
            invite_channel = server.text_channels[0]

        # Translate hours to seconds for max_age
        max_age = 3600 * inactivity_settings.get("message_invite_hours", 0)
        max_uses = inactivity_settings.get("message_invite_max_uses")
        reason = inactivity_settings.get("message_invite_reason")

        invite = await invite_channel.create_invite(max_age=max_age, max_uses=max_uses, reason=reason)
        return invite

    async def notify_members(self, context, members, message, use_case=None):
        """Sends a notice to a list of members."""
        success = []
        failed = []
        for member in members:
            notification = message

            if use_case == "inactivity":
                try:
                    invite = await self.inactivity_notification_invite(context.guild)
                    if invite:
                        notification = f"{notification}\n{invite.url}"
                except discord.HTTPException as e:
                    failed.append(member)
                    Logger.error(logger, e)
                    error_message = f"An error happened while creating invite: {e.text} (error code: {e.code})"
                    await utils.say(context.channel, content=error_message)
                    break
                except AppError as e:
                    await utils.say(context.channel, content=f"Stopped notifying members due to error:\n```{e}```")
                    return

            try:
                await utils.say(member, context=context, parse=True, content=notification)
            except discord.DiscordException as e:
                failed.append(member)
                Logger.error(logger, e)
            else:
                success.append(member)

        if success:
            messaged = "\n".join([f"{m.mention} [{m.display_name}]" for m in success])
            report_embed = discord.Embed(
                title="Notified Members",
                description=messaged
            )
            await utils.say(context.channel, embed=report_embed)
        if failed:
            not_messaged = "\n".join([f"{m.mention} [{m.display_name}]" for m in failed])
            report_embed = discord.Embed(
                title="Failed to Notify",
                description=not_messaged
            )
            notice_content = "Couldn't message the following inactive members:"
            await utils.say(context.channel, content=notice_content, embed=report_embed)

    async def notify_inactive_members(self, context, members=None):
        """Sends a notice to all inactive members."""
        message = admin_dao.inactive_message(context.guild.id)
        if not message:
            await utils.say(context.channel, content="There is no inactivity message for this server.")
            return CommandStatus.FAILED

        if not members:
            members = await get_inactive_members(context)
        members = [i.user for i in members]

        await self.notify_members(context, members, message, use_case="inactivity")
        return CommandStatus.COMPLETED

    # --- Commands ---
    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def inactivelist(self, context):
        """Show a list of inactive members."""
        cmd_settings = Settings.command_settings(context.command.name, context.guild.id)
        if not cmd_settings.get("enabled"):
            return

        inactive_members = await get_inactive_members(context)
        inactive_list = []
        for i in inactive_members:
            last_notified = i.last_notified.strftime(" (%b %d, %Y %Z)") if i.last_notified else ""
            entry = f"{'**EXEMPT** ' if i.is_exempt else ''}{i.user.mention} [{i.user.display_name}]{last_notified}"
            inactive_list.append(entry)

        days_threshold = admin_dao.inactive_threshold(context.guild.id)
        embeds = utils.split_embeds(
            title=f"Inactive Members ({days_threshold}+ days since last message)",
            description="\n".join(inactive_list)
        )

        for i, embed in enumerate(embeds):
            if i < len(embeds) - 1:
                await utils.say(context.channel, embed=embed)
            else:
                # Final message
                inactivity_message = admin_dao.inactive_message(context.guild.id)
                if inactivity_message:
                    embed.set_footer(text="React 📧 below to notify them")
                report = await utils.say(context.channel, content=f"{context.author.mention}", embed=embed)

                if inactivity_message:
                    await report.add_reaction("📧")
                    def check(reaction, user):
                        return reaction.message.id == report.id and user.id == context.message.author.id \
                        and str(reaction.emoji) == "📧"

                    try:
                        await self.bot.wait_for("reaction_add", timeout=600, check=check)
                    except asyncio.TimeoutError:
                        embed.set_footer(text=discord.Embed.Empty)
                        await report.edit(embed=embed)
                        await report.clear_reactions()
                    else:
                        await self.notify_inactive_members(context, inactive_members)

        return CommandStatus.COMPLETED

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def inactivenotify(self, context):
        """Send a notice to all inactive members."""
        cmd_settings = Settings.command_settings(context.command.name, context.guild.id)
        if not cmd_settings.get("enabled"):
            return

        await self.notify_inactive_members(context)

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def exempt(self, context):
        """Add a user to be exempt from the server's inactivity policy."""
        cmd_settings = Settings.command_settings("exempt", context.guild.id)
        if not cmd_settings.get("enabled"):
            return

        args = context.message.split(maxsplit=2)
        cmd_type = args[1].lower()
        if cmd_type == "add":
            pass
        elif cmd_type == "remove":
            pass
        elif cmd_type == "list":
            pass

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def message(self, context):
        """Send a message through the bot."""
        async def get_destination(context):
            def check_destination(msg):
                return msg.author.id == context.message.author.id \
                and msg.channel.id == context.channel.id and msg.channel_mentions

            await utils.say(context.channel, content="Which channel should the message be sent to?")
            try:
                destination = await self.bot.wait_for("message", timeout=60, check=check_destination)
                return destination.content
            except asyncio.TimeoutError:
                return False

        async def get_message(context):
            def check_message(msg):
                return msg.author.id == context.message.author.id and msg.channel.id == context.channel.id

            await utils.say(context.channel, content="What's your message?")
            try:
                message = await self.bot.wait_for("message", timeout=120, check=check_message)
                return message.content
            except asyncio.TimeoutError:
                return False

        cmd_settings = Settings.command_settings("message", context.guild.id)
        if not cmd_settings.get("enabled"):
            return

        arguments = context.message.content.split(maxsplit=2)
        destination_id = None
        msg = ""

        try:
            destination_id = arguments[1]
        except IndexError:
            destination_id = await get_destination(context)
            if not destination_id:
                return CommandStatus.CANCELLED

        destination_id = destination_id.strip("<># ")
        destination = discord.utils.find(lambda c: str(c.id) == destination_id, context.guild.text_channels)
        if not destination:
            await utils.say(context.channel, content="I couldn't find that channel on this server.")
            return CommandStatus.INVALID

        try:
            msg = arguments[2]
        except IndexError:
            msg = await get_message(context)
            if not msg:
                return CommandStatus.CANCELLED

        try:
            sent = await utils.say(destination, content=msg)
        except discord.Forbidden:
            await utils.say(context.channel, content=f"I don't have permission to send messages to {destination.name}")
            return CommandStatus.FORBIDDEN
        else:
            await utils.say(context.channel, content=f"Message sent: {sent.jump_url}")

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def edit(self, context):
        """Edit a message sent by the bot."""
        def check_id(msg):
            return msg.author.id == context.message.author.id and msg.channel.id == context.channel.id

        def check_message(msg):
            return msg.author.id == context.message.author.id and msg.channel.id == context.channel.id

        cmd_settings = Settings.command_settings("edit", context.guild.id)
        if not cmd_settings.get("enabled"):
            return

        # TODO: Let message ID be passed in first go - skip channel arg and loop through all?
        # arguments = context.message.content.split()
        message_id = 0
        if not context.message.channel_mentions:
            usage_content = "To use, put: ```;edit #[channel name]```, where [channel name] is where the message is."
            await utils.say(context.channel, content=usage_content)
            return CommandStatus.INVALID
        channel = context.message.channel_mentions[0]

        await utils.say(context.channel, content="Enter the message ID to be edited:")
        try:
            message_id = await self.bot.wait_for("message", timeout=300, check=check_id)
            message_id = message_id.content
        except asyncio.TimeoutError:
            await utils.say(context.channel, content="Time's up.")
            return CommandStatus.CANCELLED

        try:
            message_id = int(message_id)
        except ValueError:
            await utils.say(context.channel, content=f"{message_id} is not a valid message ID.")
            return CommandStatus.INVALID

        to_edit = await channel.fetch_message(message_id)
        if not to_edit:
            await utils.say(context.channel, content=f"Couldn't find message with ID #{message_id}.")
            return CommandStatus.INVALID
        elif to_edit.author.id != context.guild.me.id:
            await utils.say(context.channel, content="I can only edit messages I sent.")
            return CommandStatus.INVALID
        else:
            for preview in utils.split_embeds(
                title="Message Preview",
                description=discord.utils.escape_markdown(to_edit.content),
                url=to_edit.jump_url,
                timestamp=to_edit.edited_at if to_edit.edited_at else to_edit.created_at
            ):
                await utils.say(context.channel, embed=preview)
            await utils.say(context.channel, content="Enter the newly edited message below.")

            try:
                new_edit = await self.bot.wait_for("message", timeout=900, check=check_message)
            except asyncio.TimeoutError:
                await utils.say(context.channel, content="Time's up.")
                return CommandStatus.CANCELLED
            else:
                try:
                    await to_edit.edit(content=new_edit.content)
                except discord.Forbidden:
                    await utils.say(context.channel, content="I'm not allowed to edit this message.")
                    return CommandStatus.FORBIDDEN
                else:
                    await utils.say(context.channel, content=f"Message edited: {to_edit.jump_url}")

        return CommandStatus.COMPLETED

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def purgeleaderboard(self, context):
        """Shows which users on MEE6 leaderboard are no longer on the server."""
        cmd_settings = Settings.command_settings("purgeleaderboard", context.guild.id)
        if not cmd_settings.get("enabled"):
            return

        mee6 = mee6_py_api.API(context.guild.id)
        member_ids = [str(m.id) for m in context.guild.members]
        try:
            leaderboard_pages = await mee6.levels.get_all_leaderboard_pages()
            i = 1
            for page in leaderboard_pages:
                players = page.get("players")
                absent_members = [
                    f"**{p.get('username')}**#{p.get('discriminator')} — lv{p.get('level')}"
                    for p in players if p.get("id") not in member_ids
                ]
                if not absent_members:
                    continue

                report = discord.Embed(
                    title=f"MEE6 leaderboard members who left the server (p. {i})",
                    description="\n".join(absent_members)
                )
                await utils.say(context.channel, embed=report)
                i += 1

        except mee6_py_api.exceptions.HTTPRequestError:
            await utils.say(context.channel, content="I couldn't find this server's MEE6 leaderboard.")

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, _):
        """Shut the bot down."""
        await self.bot.logout()
        return CommandStatus.COMPLETED
