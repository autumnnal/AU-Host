from .config import TOKEN
from .bot_instance import bot
from .database import initialize_database
from .commands import *

if __name__ == "__main__":
    initialize_database()
    bot.run(TOKEN)
