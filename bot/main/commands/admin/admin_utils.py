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


async def scan_active_members(server: discord.Guild, time_boundary: datetime.Date):
    """Yields a list of active members.
    
    Args:
        server (discord.Guild): Guild object
        time_boundary (date)

    Yields:
        list: If successful, yields list of active members (discord.Member) found so far by the scan.
        discord.errors.Forbidden: If unable to access current channel, yields error.

    """
    current_scan = ActivityScan()
    include_reactions = admin_dao.include_reactions_inactivity(server.id)
    included_channels = admin_dao.inactivelist_channels(server)

    for i, channel in enumerate(included_channels):
        try:
            current_scan.current_channel = channel
            current_scan.current_channel_messages_scanned = 0

            async for message in channel.history(
                limit=None,
                after=time_boundary,
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
