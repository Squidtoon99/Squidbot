import logging 
from ink.core import SquidBot
import json

with open('./config.json', 'r') as fp:
    config = json.load(fp)

logging.basicConfig(level=logging.INFO)

SquidBot(config=config)