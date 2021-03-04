import math
import re
import discord
from main.settings import Settings

def split_embeds(title, description, url=None, timestamp=None, delimiter="\n"):
    """Returns a list of embeds split according to Discord character limits."""
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
            url=url,
            timestamp=timestamp
        ))
        starting_line = ending_line

    return embeds

def split_messages(content):
    pass

def substitute_text(text, context):
    server_name = "the server"
    if hasattr(context, "guild"):
        server = context.guild.name

    channel_name = ""
    if hasattr(context, "channel"):
        channel = context.channel.name
    
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
