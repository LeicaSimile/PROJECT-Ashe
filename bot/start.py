# -*- coding: utf-8 -*-
import errno
import logging
import logging.config
import os
import yaml
from pathlib import Path
from main.settings import Settings
from main.bot import Bot

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
    ashe = Bot(command_prefix=command_prefix, description=description)
    ashe.run()


if "__main__" == __name__:
    main()
