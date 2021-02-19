# -*- coding: utf-8 -*-
import errno
import logging
import logging.config
import os
import yaml
from pathlib import Path
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
    ashe = Bot(logger=logging.getLogger("bot"))
    ashe.run()


if "__main__" == __name__:
    main()
