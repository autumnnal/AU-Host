from bot_package.config import TOKEN
from bot_package.bot_instance import bot
from bot_package.database import initialize_database
from bot_package.commands import *

if __name__ == "__main__":
    initialize_database()
    bot.run(TOKEN)
