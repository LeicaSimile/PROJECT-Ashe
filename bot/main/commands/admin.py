import asyncio
import datetime
import time
import re

import discord
from discord.ext import commands

from main import database, settings
from main.status import CommandStatus

URL_REGEX = r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'\".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))"""

async def validate_access(context, user):
    """Checks if user has permission to use command."""
    return context.guild.owner.id == user.id \
        or user.guild_permissions.administrator \
        or discord.utils.find(
            lambda r: r.id in [settings.MOD_ROLE_ID, settings.GUILD_OWNER_ID],
            user.roles
        )

async def get_inactive_members(context, progress_report=True):
    """Returns a list of inactive members."""
    senders = []
    inactive_members = []
    now = datetime.datetime.now()
    time_boundary = now - datetime.timedelta(days=14)
    progress_msg = None
    """
    channel_count = len(context.guild.text_channels)

    if progress_report:
        progress_msg = await context.channel.send(f"Scanning {channel_count} channels for inactive members.")
    
    for i, channel in enumerate(context.guild.text_channels):
        try:
            async for m in channel.history(limit=None, after=(now - datetime.timedelta(days=14)), oldest_first=False):
                if m.author not in senders:
                    senders.append(m.author)
        except discord.errors.Forbidden:
            print(f"Can't access {channel.name}")
        else:
            if progress_msg:
                await progress_msg.edit(content=f"Scanned {i}/{channel_count} channels for inactive members.")
    
    if progress_msg:
        await progress_msg.edit(content=f"Scanned {channel_count} channels for inactive members.")
    """
    member_count = len(context.guild.members)
    if progress_report:
        progress_msg = await context.channel.send(f"Scanning {member_count} members for inactivity.")

    for i, member in enumerate(context.guild.members):
        async for msg in member.history(limit=1, oldest_first=False):
            if msg.created_at < time_boundary:
                senders.append(msg.author)
        
        if progress_msg:
            await progress_msg.edit(content=f"Scanned {i}/{member_count} members for inactivity.")
    
    results = [u for u in context.guild.members if u not in senders]
    db_inactive_members = database.get_all_inactive_members(context.guild.id)

    for member in results:
        if member.id in db_inactive_members:
            m = db_inactive_members[member.id]
            m.user = member
            inactive_members.append(m)
        else:
            inactive_members.append(database.InactiveMember(context.guild.id, member.id, user=member))
    update_inactive_members(db_inactive_members, {m.member_id: m for m in inactive_members})

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
                await member.send(content=message)
            except discord.DiscordException as e:
                failed.append(member)
                print(e.message)
            else:
                success.append(member)
        
        if success:
            messaged = "\n".join([f"{m.display_name} ({m.name}#{m.discriminator})" for m in success])
            await context.channel.send(f"Notified the following inactive members: ```{messaged}```")
        if failed:
            not_messaged = "\n".join([f"{m.display_name} ({m.name}#{m.discriminator})" for m in failed])
            await context.channel.send(f"Couldn't message the following inactive members: ```{not_messaged}```")

    async def notify_inactive_members(self, context, members=None):
        if not await validate_access(context, context.message.author):
            return CommandStatus.INVALID

        mod_role = discord.utils.find(lambda r: r.id == settings.MOD_ROLE_ID, context.guild.roles)
        if not members:
            members = await get_inactive_members(context)
        members = [i.user for i in members]
        message = f"Hello, we noticed you haven't been active for a while at ***{context.guild.name}***.\n\nWe have a policy of **kicking inactive members**, but if you're taking a break, that's alright. **Just let a moderator *(@Moderator)* know** and we'll make sure to exempt you.\n\n(Do not reply here. This is an automated message and any replies will be ignored)"

        await self.notify_members(context, members, message)
        return CommandStatus.COMPLETED

    async def validate_owner(self, context, function_pass, function_fail=None):
        """Check if the owner issued the command.

        Args:
            context (discord.Context): Context of the command.
            function_pass (func): Function to call if check passes.
                Must be a coroutine that accepts a GeneralContext object
                as an argument.
            function_fail (func, optional): Function to call if check fails.
                Must be a coroutine that accepts a GeneralContext object
                as an argument. If none provided, bot will give a stock
                warning to the user.

        """
        if str(context.author.id) == settings.OWNER_ID:
            await function_pass(context)
        else:
            try:
                await function_fail(context)
            except TypeError:
                response = "Don't tell me what to do."
                await self.bot.say(context.channel, response)
                
    @commands.command(description="Sends a list of inactive members in the server.")
    async def purgelist(self, context):
        def check(reaction, user):
            return reaction.message.id == report.id and user.id == context.message.author.id \
                and str(reaction.emoji) == "📧"

        if not await validate_access(context, context.message.author):
            return CommandStatus.INVALID

        inactive_members = await get_inactive_members(context)
        inactive_list = []
        for i in inactive_members:
            last_notified = i.last_notified.strftime(" (%b %d, %Y %Z)") if i.last_notified else ""
            entry = f"{'**EXEMPT** ' if i.is_exempt else ''}{i.user.mention} [{i.user.display_name}]{last_notified}"
            inactive_list.append(entry)

        inactive_list = "\n".join(inactive_list)
        report_embed = discord.Embed(
            title="Inactive Members (2+ weeks since last message)",
            description=inactive_list
        )
        report_embed.set_footer(text="React 📧 below to notify them")
        report = await context.channel.send(f"{context.author.mention}", embed=report_embed)
        await report.add_reaction("📧")

        try:
            reaction, user = await self.bot.client.wait_for("reaction_add", timeout=60, check=check)
        except asyncio.TimeoutError:
            report_embed.set_footer(text=discord.Embed.Empty)
            await report.edit(embed=report_embed)
            await report.clear_reactions()
        else:
            await self.notify_inactive_members(context, inactive_members)
        
        return CommandStatus.COMPLETED
    
    @commands.command(description="Notifies all purgelist members on their inactivity.")
    async def purgenotify(self, context):
        await self.notify_inactive_members(context)

    @commands.command(description="Send a message through me.")
    async def message(self, context):
        async def get_destination(context):
            def check_destination(msg):
                return msg.author.id == context.message.author.id and msg.channel.id == context.channel.id and msg.channel_mentions

            await context.channel.send("Which channel should the message be sent to?")
            try:
                destination = await self.bot.client.wait_for("message", timeout=60, check=check_destination)
                return destination.content
            except asyncio.TimeoutError:
                return False

        async def get_message(context):
            def check_message(msg):
                return msg.author.id == context.message.author.id and msg.channel.id == context.channel.id

            await context.channel.send("What's your message?")
            try:
                message = await self.bot.client.wait_for("message", timeout=120, check=check_message)
                return message.content
            except asyncio.TimeoutError:
                return False

        if not await validate_access(context, context.message.author):
            return CommandStatus.INVALID

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
            await context.channel.send("I couldn't find that channel on this server.")
            return CommandStatus.INVALID

        try:
            msg = arguments[2]
        except IndexError:
            msg = await get_message(context)
            if not msg:
                return CommandStatus.CANCELLED
        
        try:
            sent = await destination.send(msg)
        except discord.Forbidden:
            await context.channel.send(f"I don't have permission to send messages to {destination.name}")
            return CommandStatus.FORBIDDEN
        else:
            await context.channel.send(f"Message sent: {sent.jump_url}")

    @commands.command(
        description="Edit a message sent through me.",
        usage="#[channel name]",
        help="""Paste the message ID when prompted, then enter the new message.

        To get the message ID, enable developer mode in App Settings > Appearance > Advanced > Developer Mode.
        
        (PC) Hover to the right of the message and click the three vertical dots > Copy ID.
        (Mobile) Tap and hold the message > Copy ID.
        """
    )
    async def edit(self, context):
        def check_id(msg):
            return msg.author.id == context.message.author.id and msg.channel.id == context.channel.id

        def check_message(msg):
            return msg.author.id == context.message.author.id and msg.channel.id == context.channel.id

        if not await validate_access(context, context.message.author):
            return

        arguments = context.message.content.split()
        message_id = 0
        if not context.message.channel_mentions:
            await context.channel.send("To use, put: ```;edit #[channel name]```, where [channel name] is where the message is.")
            return CommandStatus.INVALID
        channel = context.message.channel_mentions[0]

        await context.channel.send("Enter the message ID to be edited:")
        try:
            message_id = await self.bot.client.wait_for("message", timeout=300, check=check_id)
            message_id = message_id.content
        except asyncio.TimeoutError:
            await context.channel.send("Time's up.")
            return CommandStatus.CANCELLED

        try:
            message_id = int(message_id)
        except ValueError:
            await context.channel.send(f"{message_id} is not a valid message ID.")
            return CommandStatus.INVALID

        to_edit = await channel.fetch_message(message_id)
        if not to_edit:
            await context.channel.send(f"Couldn't find message with ID #{message_id}.")
            return CommandStatus.INVALID
        elif to_edit.author.id != context.guild.me.id:
            await context.channel.send("I can only edit messages I sent.")
            return CommandStatus.INVALID
        else:
            preview = discord.Embed(
                title="Message Preview",
                url=to_edit.jump_url,
                description=discord.utils.escape_markdown(to_edit.content),
                timestamp=to_edit.edited_at if to_edit.edited_at else to_edit.created_at
            )
            await context.channel.send(content="Enter the newly edited message below.", embed=preview)
            try:
                new_edit = await self.bot.client.wait_for("message", timeout=300, check=check_message)
            except asyncio.TimeoutError:
                await context.channel.send("Time's up.")
                return CommandStatus.CANCELLED
            else:
                try:
                    await to_edit.edit(content=new_edit.content)
                except discord.Forbidden:
                    await context.channel.send("I'm not allowed to edit this message.")
                    return CommandStatus.FORBIDDEN
                else:
                    await context.channel.send(f"Message edited: {to_edit.jump_url}")

        return CommandStatus.COMPLETED

    @commands.command()
    async def test_multiwait(self, context):
        done = False

        def check_reaction(reaction, user):
            return reaction.message.id == report.id and user.id == context.message.author.id \
                and str(reaction.emoji) == "✅"

        async def edit_base(base_msg, embed, timeout):
            def check_message(msg):
                return msg.author.id == context.message.author.id and msg.channel.id == context.channel.id

            try:
                new_edit = await self.bot.client.wait_for("message", timeout=timeout, check=check_message)
            except asyncio.TimeoutError:
                pass
            else:
                if not done:
                    embed.description = new_edit.clean_content
                    await base_msg.edit(embed=embed)
                    await edit_base(base_msg, embed, timeout)

        preview = discord.Embed(
            title="Message Preview",
            description="DRY BANANA HIPPY HAT"
        )
        base_msg = await context.channel.send(
            "Type new edits below.\nReact with ✅ to confirm change.", embed=preview
        )
        await base_msg.add_reaction("✅")

        timeout = 60
        await edit_base(base_msg, preview, timeout)

        try:
            reaction, user = await self.bot.client.wait_for("reaction_add", timeout=timeout, check=check_reaction)
        except asyncio.TimeoutError:
            await base_msg.clear_reactions()
        else:
            await context.channel.send("All done.")
        finally:
            done = True

        return CommandStatus.COMPLETED

    @commands.command(description="Shut me down :c")
    async def shutdown(self, context):
        async def log_out(context):
            try:
                response = ""
                await self.bot.say(context.channel, response, context)
            finally:
                await self.bot.client.logout()
                return CommandStatus.COMPLETED

        async def sass(context):
            response = "Don't tell me what to do."
            await self.bot.say(context.channel, response)
            return CommandStatus.INVALID

        await self.validate_owner(context, log_out, sass)
    