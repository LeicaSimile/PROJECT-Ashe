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
    pages = math.ceil((char_count * 1.0) / Settings.app_standards("embed")["description_limit"])
    split_description = description.split(delimiter)
    
    starting_line = 0
    for p in range(1, pages + 1):
        ending_line = math.ceil((len(split_description) / pages) * p)
        embeds.append(discord.Embed(
            title=title,
            description=delimiter.join(split_description[starting_line:ending_line]),
            **kwargs
        ))
        starting_line = ending_line

    return embeds

def split_messages(content):
    pass

def substitute_text(text: str, context: discord.ext.commands.Context):
    server_name = "the server"
    if hasattr(context, "guild"):
        server_name = context.guild.name

    channel_name = ""
    if hasattr(context, "channel"):
        channel_name = context.channel.name
    
    mention = ""
    if hasattr(context, "mention"):
        mention = context.mention

    substitutions = {
        "server": server_name,
        "channel": channel_name,
        "mention": mention
    }
    text = text.format(**substitutions)
    try:
        re_channels = set(re.findall(r"\[#(.+?)\]", text))
        for c in re_channels:
            c_object = discord.utils.get(context.guild.channels, name=c)
            if c_object:
                text = text.replace(f"[#{c}]", c_object.mention)
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
                for f in embed.fields:
                    f.value = substitute_text(f.value, context)
            kwargs["embed"] = embed

    return await channel.send(**kwargs)