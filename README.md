# Among Us Discord Bot

A Discord bot for creating, editing, listing, and managing Among Us lobby announcements.

The bot uses PostgreSQL for persistent storage.

## Local setup

1. Install Python 3.12 or newer.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env`.
4. Put your Discord bot token in `.env`:

   ```env
   DISCORD_TOKEN=your_token_here
   DATABASE_URL=postgresql://user:password@host:5432/database
   ```

5. Start the bot:

   ```bash
   python run_bot.py
   ```

## Railway deployment

1. Push this repository to GitHub.
2. In Railway, create a new project and choose **Deploy from GitHub Repo**.
3. Select this repository.
4. Add the variable `DISCORD_TOKEN` in the Railway service's Variables tab.
5. Deploy. Railway will use the included `Dockerfile` and `railway.toml`.

### PostgreSQL persistence

The bot uses PostgreSQL through the `DATABASE_URL` environment variable. In Railway, add a PostgreSQL database to the project, then reference its connection URL in the bot service's Variables tab. Railway commonly provides this as `${{Postgres.DATABASE_URL}}` when using a variable reference.

The database tables are created automatically on startup. Do not commit `.env` files or database credentials to GitHub.
