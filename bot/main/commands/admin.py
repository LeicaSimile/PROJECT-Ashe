import asyncio
import datetime
import math
import time
import re

import discord
from discord.ext import commands
import mee6_py_api

from main import database, utils
from main.settings import Settings
from main.status import CommandStatus

URL_REGEX = r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'\".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))"""

async def validate_access(context, user):
    """Checks if user has permission to use command."""
    return context.guild.owner.id == user.id \
        or user.guild_permissions.administrator

async def get_inactive_members(context, progress_report=True):
    """Returns a list of inactive members."""
    senders = []
    inactive_members = []
    now = datetime.datetime.now()
    days_threshold = Settings.inactive_threshold(context.guild.id)
    time_boundary = now - datetime.timedelta(days=days_threshold)
    progress_msg = None
    include_reactions = Settings.include_reactions_inactivity(context.guild.id)

    included_channels = context.guild.text_channels
    channel_count = len(included_channels)

    if progress_report:
        progress_msg = await utils.say(context.channel, content=f"Scanning {channel_count} channels for inactive members.")
    
    for i, channel in enumerate(included_channels):
        try:
            async for m in channel.history(limit=None, after=(now - datetime.timedelta(days=days_threshold)), oldest_first=False):
                if m.author not in senders:
                    senders.append(m.author)

                if include_reactions:
                    for r in m.reactions:
                        async for u in r.users:
                            if u not in senders:
                                senders.append(u)

        except discord.errors.Forbidden:
            print(f"Can't access {channel.name}")
        else:
            if progress_msg:
                await progress_msg.edit(content=f"Scanned {i}/{channel_count} channels for inactive members.")
    
    if progress_msg:
        await progress_msg.edit(content=f"Scanned {channel_count} channels for inactive members.")
    
    results = [
        u for u in context.guild.members
        if u not in senders and u.joined_at < time_boundary and not u.bot
    ]
    db_inactive_members = [] # database.get_all_inactive_members(context.guild.id)

    for member in results:
        if member.id in db_inactive_members:
            m = db_inactive_members[member.id]
            m.user = member
            inactive_members.append(m)
        else:
            inactive_members.append(database.InactiveMember(context.guild.id, member.id, user=member))
    # update_inactive_members(db_inactive_members, {m.member_id: m for m in inactive_members})

    return inactive_members

def update_inactive_members(before, after):
    """
    Args:
        before(dict): Collection of previously recorded inactive members {member_id: database.InactiveMember}.
        after(dict): Current collection of inactive members {member_id: database.InactiveMember}.

    """
    for member in before:
        if member not in after:
            database.remove_inactive_member(before[member].guild_id, before[member].member_id)

    for member in after:
        if member not in before:
            database.add_inactive_member(after[member].guild_id, after[member].member_id)

    return


class Admin(commands.Cog):
    """Commands usable only by the admin."""

    def __init__(self, bot):
        """
        Args:
            bot(Bot): Bot instance.
            
        """
        self.bot = bot

    async def notify_members(self, context, members, message):
        success = []
        failed = []
        for member in members:
            try:
                await utils.say(member, content=message)
            except discord.DiscordException as e:
                failed.append(member)
                print(e)
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
            await utils.say(context.channel, content=f"Couldn't message the following inactive members:", embed=report_embed)

    async def notify_inactive_members(self, context, members=None):
        if not await validate_access(context, context.message.author):
            return CommandStatus.INVALID

        message = Settings.inactive_message(context.guild.id)
        if not message:
            await utils.say(context.channel, content="There is no inactivity message for this server.")
            return CommandStatus.FAILED

        if not members:
            members = await get_inactive_members(context)
        members = [i.user for i in members]
        
        await self.notify_members(context, members, message)
        return CommandStatus.COMPLETED
                
    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def inactivelist(self, context):
        cmd_settings = Settings.command_settings(context.command.name, context.guild.id)
        if not cmd_settings.get("enabled"):
            return

        inactive_members = await get_inactive_members(context)
        inactive_list = []
        for i in inactive_members:
            last_notified = i.last_notified.strftime(" (%b %d, %Y %Z)") if i.last_notified else ""
            entry = f"{'**EXEMPT** ' if i.is_exempt else ''}{i.user.mention} [{i.user.display_name}]{last_notified}"
            inactive_list.append(entry)

        days_threshold = Settings.inactive_threshold(context.guild.id)
        embeds = utils.split_embeds(
            title=f"Inactive Members ({days_threshold}+ days since last message)",
            description="\n".join(inactive_list)
        )

        for i, embed in enumerate(embeds):
            if i < len(embeds) - 1:
                await utils.say(context.channel, embed=embed)
            else:
                # Final message
                inactivity_message = Settings.inactive_message(context.guild.id)
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
        cmd_settings = Settings.command_settings(context.command.name, context.guild.id)
        if not cmd_settings.get("enabled"):
            return

        await self.notify_inactive_members(context)

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def exempt(self, context):
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
        async def get_destination(context):
            def check_destination(msg):
                return msg.author.id == context.message.author.id and msg.channel.id == context.channel.id and msg.channel_mentions

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
            await utils.say(context.channel, content="To use, put: ```;edit #[channel name]```, where [channel name] is where the message is.")
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
                absent_members = [f"**{p.get('username')}**#{p.get('discriminator')} — lv{p.get('level')}" for p in players if p.get("id") not in member_ids]
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
    async def shutdown(self, context):
        await self.bot.logout()
        return CommandStatus.COMPLETED
