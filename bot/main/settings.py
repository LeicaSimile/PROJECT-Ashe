import logging
import os
import yaml
from pathlib import Path

logger = logging.getLogger("bot")
app_config = None
events_config = None

def load_config(filename):
    with open(Path(__file__).parent.joinpath("config", filename), "r") as f:
        return yaml.safe_load(f.read())

def load_all():
    app_config_filename = "app.yaml"
    events_config_filename = "events.yaml"
    
    global app_config
    global events_config
    app_config = load_config(app_config_filename)
    events_config = load_config(events_config_filename)

# Read config files to set variables accordingly
load_all()

defaults = app_config["default"]
CMD_PREFIX = defaults["cmd_prefix"]
DESCRIPTION = defaults["description"]
DEFAULT_STATUS = defaults["status"]

embed_constants = app_config["constants"]["embed"]
EMBED_TITLE_LIMIT = embed_constants["title_limit"]
EMBED_DESCRIPTION_LIMIT = embed_constants["description_limit"]
EMBED_FIELD_LIMIT = embed_constants["field_limit"]
EMBED_FIELD_NAME_LIMIT = embed_constants["field_name_limit"]
EMBED_FIELD_VALUE_LIMIT = embed_constants["field_value_limit"]
EMBED_FOOTER_LIMIT = embed_constants["footer_limit"]
EMBED_AUTHOR_NAME_LIMIT = embed_constants["author_name_limit"]
EMBED_CHARACTER_LIMIT = embed_constants["total_character_limit"]

dict_constants = app_config["constants"]["define"]
DICT_REGULAR_CACHE_LIMIT = dict_constants["regular"].get("cache_limit", 1000)
DICT_REGULAR_API_URL = dict_constants["regular"]["base_api_url"]
DICT_REGULAR_URL = dict_constants["regular"]["base_url"]

# Grab environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
CLIENT_TOKEN = os.environ.get("CLIENT_TOKEN")
OWNER_ID = os.environ.get("OWNER_ID")

DICT_REGULAR_API_KEY = os.environ.get("DICT_REGULAR_API_KEY")
DICT_ELEMENTARY_API_KEY = os.environ.get("DICT_ELEMENTARY_API_KEY")

MOD_ROLE_ID = 535886249458794547

def get_constants():
    """Returns app constants as a Python object"""
    return app_config["constants"]

def get_default_config():
    """Returns default event configuration as a Python object"""
    return events_config["default"]

def get_server_config(server_id):
    """Returns event configuration for a given server (gives None if config doesn't exist)"""
    return events_config["servers"].get(server_id)

def get_inactive_threshold(server_id=None):
    if server_id:
        server_config = get_server_config(server_id)
        if server_config and "inactivity" in server_config:
            try:
                return server_config["inactivity"]["days_threshold"]
            except KeyError as err:
                logger.debug(f"'inactivity' config for server ID {server_id} is missing a setting for 'days_threshold'. Using default setting instead.")
    
    try:
        return get_default_config()["inactivity"]["days_threshold"]
    except KeyError as err:
        logger.warn(f"{events_config_filename} is missing a default setting for 'inactivity': 'days_threshold'. {err}")
        return 14

def get_inactive_message(server_id):
    default_config = get_default_config()
    server_config = get_server_config(server_id)
    if server_config and "inactivity" in server_config:
        if server_config["inactivity"].get("message_enabled",
            default_config["inactivity"]["message_enabled"]
        ):
            try:
                return server_config["inactivity"]["message"]
            except KeyError as err:
                logger.debug(f"'inactivity' config for server ID {server_id} is missing a setting for 'message'. Using default setting instead.")

            return default_config["inactivity"]["message"]
    
    return None

def include_reactions_inactivity(server_id=None):
    if server_id:
        server_config = get_server_config(server_id)
        if server_config and "inactivity" in server_config:
            try:
                return server_config["inactivity"]["include_reactions"]
            except KeyError as err:
                logger.debug(f"'inactivity' config for server ID {server_id} is missing a setting for 'include_reactions'. Using default setting instead.")
    
    try:
        return get_default_config()["inactivity"]["include_reactions"]
    except KeyError as err:
        logger.warn(f"{events_config_filename} is missing a default setting for 'inactivity: include_reactions'. {err}")
        return True
