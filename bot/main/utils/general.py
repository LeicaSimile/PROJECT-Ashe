"""General-purpose helper functions for the bot"""
import math
import re
import discord
from main.settings import Settings

def split_embeds(title: str, description: str, delimiter="\n", **kwargs):
    """Returns a list of embeds split according to Discord character limits.

    Args:
        title(str): Title of the embed
        description(str): Embed description (body text)
    """
    embeds = []
    char_count = len(description)
    max_chars = Settings.app_standards("embed")["description_limit"]
    current_count = 0

    # Minimum length of description as percentage of max_chars (0 to 1)
    # e.g. 0.5 = description length must be at least 50% of max_chars
    min_threshold = 0.25

    while current_count < char_count:
        current_description = description[current_count:]
        if len(current_description) > max_chars:
            end = current_count + max_chars
            current_description = description[current_count:end]
            split_description = current_description.rsplit(delimiter, maxsplit=1)
            if len(split_description) < 2 or len(split_description[0]) < (max_chars * min_threshold):
                split_description = current_description.rsplit(maxsplit=1)
                if len(split_description) > 1:
                    current_count += 1
            elif len(split_description) > 1:
                current_count += len(delimiter)

            current_description = split_description[0]
        
        current_count += len(current_description)
        embeds.append(discord.Embed(
            title=title,
            description=current_description,
            **kwargs
        ))

    return embeds

def split_messages(content):
    """Returns a list of messages split according to Discord character limits."""

def substitute_text(text: str, context: discord.ext.commands.Context):
    """Replaces placeholders in text with their intended values."""
    server_name = "the server"
    owner_name = "the server owner"
    owner_discriminator = ""
    if hasattr(context, "guild"):
        server_name = context.guild.name
        owner_name = context.guild.owner.name
        owner_discriminator = context.guild.owner.discriminator

    channel_name = ""
    if hasattr(context, "channel"):
        channel_name = context.channel.name

    mention = ""
    if hasattr(context, "mention"):
        mention = context.mention

    substitutions = {
        "server": server_name,
        "channel": channel_name,
        "mention": mention,
        "owner_name": owner_name,
        "owner_discriminator": owner_discriminator
    }
    text = text.format(**substitutions)
    try:
        re_channels = set(re.findall(r"\[#(.+?)\]", text))
        for re_channel in re_channels:
            channel_object = discord.utils.get(context.guild.channels, name=re_channel)
            if channel_object:
                text = text.replace(f"[#{re_channel}]", channel_object.mention)
    except AttributeError:
        pass

    return text

async def say(channel: discord.abc.Messageable, context: discord.ext.commands.Context=None, parse=False, **kwargs):
    """
    Args:
        channel(discord.abc.Messageable): The message's destination (e.g. TextChannel, DMChannel, etc.)
        context(discord.ext.commands.Context): The original context of the message
        **kwargs: Any arguments accepted by discord.Channel.send()
    """
    if parse and context:
        content = kwargs.get("content")
        embed = kwargs.get("embed")

        if content:
            kwargs["content"] = substitute_text(content, context)
        if embed:
            if embed.title:
                embed.title = substitute_text(embed.title, context)
            if embed.description:
                embed.description = substitute_text(embed.description, context)
            if embed.footer:
                embed.footer.text = substitute_text(embed.footer.text, context)
            if embed.fields:
                for field in embed.fields:
                    field.value = substitute_text(field.value, context)
            kwargs["embed"] = embed

    return await channel.send(**kwargs)
