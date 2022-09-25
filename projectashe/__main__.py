# -*- coding: utf-8 -*-
import errno
import logging
import logging.config
import os
import yaml
import discord
from pathlib import Path
from projectashe.settings import Settings
from projectashe.bot import Bot

try:
    os.makedirs("logs")
except OSError as e:
    if e.errno != errno.EEXIST:
        raise

with open(Path(__file__).parent.joinpath("logging.yaml"), "r") as f:
    log_config = yaml.safe_load(f.read())
logging.config.dictConfig(log_config)

def main():
    command_prefix = Settings.app_defaults("cmd_prefix")
    description = Settings.app_defaults("description")
    status = Settings.app_defaults("status").format(prefix=command_prefix)
    ashe = Bot(command_prefix=command_prefix, description=description, activity=discord.Game(name=status))
    ashe.run()


if __name__ == "__main__":
    main()
