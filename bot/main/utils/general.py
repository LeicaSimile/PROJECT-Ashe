import logging
import math
import discord
from main.settings import Settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def log(message, log_level, log_object=logging, *args, **kwargs):
    log_map = {
        logging.DEBUG: log_object.debug,
        logging.INFO: log_object.info,
        logging.WARN: log_object.warn,
        logging.ERROR: log_object.error,
        logging.CRITICAL: log_object.critical,
    }
    try:
        log_map[log_level](message, *args, **kwargs)
    except UnicodeEncodeError:
        log_map[log_level](message.encode("utf-8", errors="replace"), *args, **kwargs)
    except AttributeError as invalid_arg_err:
        logger.error(invalid_arg_err)

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
