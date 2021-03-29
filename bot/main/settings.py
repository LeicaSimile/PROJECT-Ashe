import logging
import os
from pathlib import Path
import yaml
from main.logger import Logger

logger = logging.getLogger(__name__)

class Settings():
    """Class for accessing values from config files"""
    config = {}

    @staticmethod
    def load_config(filename):
        with open(Path(__file__).parent.joinpath("config", filename), "r") as f:
            return yaml.safe_load(f.read())

    @classmethod
    def load_all(cls):
        app_config_filename = ""
        features_config_filename = ""

        cls.config = {
            "app": {},
            "features": {},
            "env": {
                "environment": os.environ.get("ENVIRONMENT"),
                "database_url": os.environ.get("DATABASE_URL"),
                "client_id": os.environ.get("CLIENT_ID"),
                "client_secret": os.environ.get("CLIENT_SECRET"),
                "client_token": os.environ.get("CLIENT_TOKEN"),
                "dict_regular_api_key": os.environ.get("DICT_REGULAR_API_KEY"),
            }
        }

        app_environment = cls.config["env"]["environment"]
        if app_environment == "PROD":
            app_config_filename = "app.yaml"
            features_config_filename = "features.yaml"
        elif app_environment == "DEV":
            app_config_filename = "app_dev.yaml"
            features_config_filename = "features_dev.yaml"

        cls.config["app"] = cls.load_config(app_config_filename)
        cls.config["features"] = cls.load_config(features_config_filename)

    @classmethod
    def app_defaults(cls, key=""):
        values = cls.config["app"]["default"]
        if key:
            values = values.get(key)

        return values

    @classmethod
    def app_standards(cls, key=""):
        values = cls.config["app"]["standards"]
        if key:
            values = values.get(key)

        return values

    @classmethod
    def default_features(cls, feature=""):
        """Returns default features configuration as a Python object"""
        values = cls.config["features"]["default"]
        if feature:
            values = values.get(feature)

        return values

    @classmethod
    def server_features(cls, server_id, feature=""):
        """Returns event configuration for a given server (gives None if config doesn't exist)"""
        values = cls.config["features"]["servers"].get(server_id)
        if feature and values:
            values = values.get(feature)

        return values

    @classmethod
    def on_message_features(cls, server_id, feature):
        default_features = cls.default_features("on_message")
        server_features = cls.server_features(server_id, "on_message")
        if not server_features:
            return None

        server_settings = server_features.get(feature)
        if not server_settings:
            return None

        # Combine default settings with server settings if not present already
        if default_features:
            default_settings = default_features.get(feature)
            if default_settings:
                for value in [v for v in default_settings if v not in server_settings]:
                    server_settings[value] = default_settings[value]

        return server_settings

    @classmethod
    def on_member_update_features(cls, server_id, feature):
        default_features = cls.default_features("on_member_update")
        server_features = cls.server_features(server_id, "on_member_update")
        if not server_features:
            return None

        server_settings = server_features.get(feature)
        if not server_settings:
            return None

        # Combine default settings with server settings if not present already
        if default_features:
            default_settings = default_features.get(feature)
            if default_settings:
                for value in [v for v in default_settings if v not in server_settings]:
                    server_settings[value] = default_settings[value]

        return server_settings

    @classmethod
    def command_settings(cls, command, server_id=None):
        if server_id is not None:
            cmd_settings = cls.server_features(server_id, "commands")
            if cmd_settings:
                return cmd_settings.get(command)

        return cls.default_features("commands").get(command)


# Read config files to set variables accordingly
Settings.load_all()
