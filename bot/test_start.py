import yaml
from pathlib import Path
#from main import database

events_config = None
with open(Path(__file__).parent.joinpath("main/config/events.yaml"), "r") as f:
    events_config = yaml.safe_load(f.read())

#print(database.get_all_inactive_members(1))
