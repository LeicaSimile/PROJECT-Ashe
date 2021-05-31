import datetime
import discord
from . import admin_dao

class ActivityScan():
    """Object containing info about server activity scan's current progress.

    Attributes:
        current_message (discord.Message): Current message being scanned.
        current_channel (discord.TextChannel): Current channel being scanned.
        current_channel_messages_scanned (int): Number of messages that have already been scanned in current channel.
        error (discord.DiscordException): Current error being thrown (Resets to None if no errors).
        active_members (list of discord.Member): List of members identified as active on the server during scan.

    """
    def __init__(self):
        self.current_message = None
        self.current_channel = None
        self.current_channel_messages_scanned = 0
        self.error = None
        self.active_members = []

    @property
    def message_time(self):
        if self.current_message:
            return self.current_message.created_at.strftime("%b %d, %H:%M %Z")
        return ""


async def scan_active_members(server: discord.Guild):
    """Yields a list of active members.
    
    Args:
        server (discord.Guild): Guild object

    Yields:
        list: If successful, yields list of active members (discord.Member) found so far by the scan.
        discord.errors.Forbidden: If unable to access current channel, yields error.

    """
    current_scan = ActivityScan()
    now = datetime.datetime.now()
    days_threshold = admin_dao.inactive_threshold(server.id)
    time_boundary = now - datetime.timedelta(days=days_threshold)

    include_reactions = admin_dao.include_reactions_inactivity(server.id)
    included_channels = admin_dao.inactivelist_channels(server)

    for i, channel in enumerate(included_channels):
        try:
            current_scan.current_channel = channel
            current_scan.current_channel_messages_scanned = 0

            async for message in channel.history(
                limit=None,
                after=(now - datetime.timedelta(days=days_threshold)),
                oldest_first=True
             ):
                current_scan.error = None
                current_scan.current_message = message
                if message.author not in current_scan.active_members:
                    current_scan.active_members.append(message.author)

                if include_reactions:
                    for react in message.reactions:
                        async for user in react.users():
                            if user not in current_scan.active_members:
                                current_scan.active_members.append(user)

                current_scan.current_channel_messages_scanned += 1
                yield current_scan

        except discord.errors.Forbidden as err_forbidden:
            current_scan.error = err_forbidden
            yield current_scan

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

    async for scan in admin_dao.scan_active_members(context.guild):
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

            update_interval = 50
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