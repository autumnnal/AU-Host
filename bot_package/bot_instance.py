import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.guilds = True
intents.members = True


class Bot(commands.Bot):
    async def setup_hook(self):
        guild_id = os.getenv("GUILD_ID")

        if guild_id:
            guild = discord.Object(id=int(guild_id))

            # Copy the commands to your development server
            self.tree.copy_global_to(guild=guild)

            # Register them immediately in that server
            synced = await self.tree.sync(guild=guild)

            print(f"Synced {len(synced)} commands to guild {guild_id}")
        else:
            # Fallback: register globally
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} global commands")


bot = Bot(command_prefix='!', intents=intents)
