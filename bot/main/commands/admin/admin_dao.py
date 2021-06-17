"""Methods for accessing data related to admin features."""
import datetime
import logging
import discord
from main.settings import Settings
from main.logger import Logger

logger = logging.getLogger(__name__)


def server_inactivity_settings(server_id):
    """Returns a server's inactivity configuration"""
    default_features = Settings.default_features("inactivity")
    server_features = Settings.server_features(server_id, "inactivity")
    if not server_features:
        return default_features
    
    # Combine default settings with server settings if not present already
    if default_features:
        for value in default_features:
            if value not in server_features:
                server_features[value] = default_features[value]

    return server_features

def inactive_threshold(server_id=None):
    """Returns the minimum amount of days for a server member to be considered inactive."""
    if server_id:
        server_config = Settings.server_features(server_id, "inactivity")
        if server_config:
            try:
                return server_config["days_threshold"]
            except KeyError as err:
                Logger.debug(logger, f"'inactivity' config for server ID {server_id} is missing a setting for 'days_threshold'. Using default setting instead.")
    
    try:
        return Settings.default_features("inactivity")["days_threshold"]
    except KeyError as err:
        Logger.warn(logger, f"Missing a default setting for 'inactivity' feature: 'days_threshold'. {err}")
        return 14

def inactive_message(server_id):
    default_config = Settings.default_features("inactivity")
    server_config = Settings.server_features(server_id, "inactivity")
    message_enabled = default_config["message_enabled"]
    if server_config:
        message_enabled = server_config.get("message_enabled", message_enabled)
        
    if message_enabled:
        if server_config:
            try:
                return server_config["message"]
            except KeyError:
                Logger.debug(logger, f"'inactivity' config for server ID {server_id} is missing a setting for 'message'. Using default setting instead.")
        
        return default_config["message"]
    
    return None

def include_reactions_inactivity(server_id=None):
    if server_id:
        server_config = Settings.server_features(server_id, "inactivity")
        if server_config:
            try:
                return server_config["include_reactions"]
            except KeyError as err:
                Logger.debug(logger, f"'inactivity' config for server ID {server_id} is missing a setting for 'include_reactions'. Using default setting instead.")
    
    try:
        return Settings.default_features("inactivity")["include_reactions"]
    except KeyError as err:
        Logger.warn(logger, f"Missing a default setting for 'inactivity: include_reactions'. {err}")
    
    return True

def inactivelist_channels(server: discord.Guild):
    return server.text_channels

def update_inactive_members(server_id: int, new_inactive_members):
    pass
