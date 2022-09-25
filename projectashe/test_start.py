import yaml
from pathlib import Path
#from projectashe import database

events_config = None
with open(Path(__file__).parent.joinpath("config/events.yaml"), "r") as f:
    events_config = yaml.safe_load(f.read())

message = r"{server}"
message = message.format(server="LMF")
print(message)
#print(database.get_all_inactive_members(1))
