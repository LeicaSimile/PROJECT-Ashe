import math
import discord
from main import settings

def split_embeds(title, description, url=None, timestamp=None, delimiter="\n"):
    """Returns a list of embeds split according to Discord character limits."""
    embeds = []
    char_count = len(description)
    pages = math.ceil((char_count * 1.0) / settings.EMBED_DESCRIPTION_LIMIT)
    split_description = description.split(delimiter)
    
    starting_line = 0
    for p in range(1, pages):
        ending_line = math.ceil((len(split_description) / pages) * p)
        embeds.append(embed=discord.Embed(
            title=title,
            description=delimiter.join(split_description[starting_line:ending_line]),
            url=url,
            timestamp=timestamp
        ))
        starting_line = ending_line

    return embeds

def split_messages(content):
    pass
