import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN: raise RuntimeError('DISCORD_TOKEN is missing. Check your .env file.')
ROLE_OPTIONS = {'role_one': 1487539248788668619, 'role_two': 1488233654978351326}
