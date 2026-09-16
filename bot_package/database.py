import os
import psycopg
from psycopg.rows import dict_row
from typing import Optional


# ==================================================
# DATABASE
# ==================================================

def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing. Add your Railway PostgreSQL connection string.")
    return psycopg.connect(database_url, row_factory=dict_row)


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lobby_layouts (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                settings TEXT NOT NULL DEFAULT '',
                rules TEXT NOT NULL DEFAULT '',
                extra_info TEXT NOT NULL DEFAULT '',
                ping_role_id INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS server_settings (
                guild_id INTEGER PRIMARY KEY,
                default_rules TEXT NOT NULL DEFAULT ''
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS host_stats (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                hosted_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lobby_queue (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, guild_id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS active_lobbies (
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                host_id INTEGER NOT NULL,
                lobby_code TEXT NOT NULL,
                settings TEXT NOT NULL,
                rules TEXT NOT NULL,
                extra_info TEXT NOT NULL,
                selected_role_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, message_id)
            )
            """
        )

        connection.commit()


def get_saved_layout(
    user_id: int,
    guild_id: int
) -> Optional[dict]:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT settings, rules, extra_info, ping_role_id
            FROM lobby_layouts
            WHERE user_id = %s AND guild_id = %s
            """,
            (user_id, guild_id),
        )

        return cursor.fetchone()


def save_layout(
    user_id: int,
    guild_id: int,
    settings: str,
    rules: str,
    extra_info: str,
    ping_role_id: int,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO lobby_layouts (
                user_id,
                guild_id,
                settings,
                rules,
                extra_info,
                ping_role_id
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT(user_id, guild_id)
            DO UPDATE SET
                settings = excluded.settings,
                rules = excluded.rules,
                extra_info = excluded.extra_info,
                ping_role_id = excluded.ping_role_id
            """,
            (
                user_id,
                guild_id,
                settings,
                rules,
                extra_info,
                ping_role_id,
            ),
        )

        connection.commit()


def delete_layout(user_id: int, guild_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM lobby_layouts
            WHERE user_id = %s AND guild_id = %s
            """,
            (user_id, guild_id),
        )

        connection.commit()


def get_default_rules(guild_id: int) -> str:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT default_rules
            FROM server_settings
            WHERE guild_id = %s
            """,
            (guild_id,),
        )

        row = cursor.fetchone()

        if row:
            return row["default_rules"]

        return ""


def save_default_rules(guild_id: int, rules: str):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO server_settings (
                guild_id,
                default_rules
            )
            VALUES (%s, %s)
            ON CONFLICT(guild_id)
            DO UPDATE SET
                default_rules = excluded.default_rules
            """,
            (guild_id, rules),
        )

        connection.commit()


def increment_host_stats(user_id: int, guild_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO host_stats (
                user_id,
                guild_id,
                hosted_count
            )
            VALUES (%s, %s, 1)
            ON CONFLICT(user_id, guild_id)
            DO UPDATE SET
                hosted_count = hosted_count + 1
            """,
            (user_id, guild_id),
        )

        connection.commit()


def get_user_host_count(user_id: int, guild_id: int) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT hosted_count
            FROM host_stats
            WHERE user_id = %s AND guild_id = %s
            """,
            (user_id, guild_id),
        )

        row = cursor.fetchone()

        return row["hosted_count"] if row else 0


def get_leaderboard(guild_id: int):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT user_id, hosted_count
            FROM host_stats
            WHERE guild_id = %s
            ORDER BY hosted_count DESC
            LIMIT 10
            """,
            (guild_id,),
        )

        return cursor.fetchall()


def add_to_queue(user_id: int, guild_id: int) -> bool:
    with get_connection() as connection:
        try:
            connection.execute(
                """
                INSERT INTO lobby_queue (
                    user_id,
                    guild_id
                )
                VALUES (%s, %s)
                """,
                (user_id, guild_id),
            )

            connection.commit()
            return True

        except psycopg.errors.UniqueViolation:
            return False


def remove_from_queue(user_id: int, guild_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM lobby_queue
            WHERE user_id = %s AND guild_id = %s
            """,
            (user_id, guild_id),
        )

        connection.commit()

        return cursor.rowcount > 0


def get_queue(guild_id: int):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT user_id
            FROM lobby_queue
            WHERE guild_id = %s
            ORDER BY joined_at ASC
            """,
            (guild_id,),
        )

        return [row["user_id"] for row in cursor.fetchall()]


def clear_queue(guild_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM lobby_queue
            WHERE guild_id = %s
            """,
            (guild_id,),
        )

        connection.commit()


def save_active_lobby(
    guild_id: int,
    channel_id: int,
    message_id: int,
    host_id: int,
    lobby_code: str,
    settings: str,
    rules: str,
    extra_info: str,
    selected_role_id: int,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO active_lobbies (
                guild_id,
                channel_id,
                message_id,
                host_id,
                lobby_code,
                settings,
                rules,
                extra_info,
                selected_role_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (guild_id, message_id)
            DO UPDATE SET
                channel_id = EXCLUDED.channel_id,
                host_id = EXCLUDED.host_id,
                lobby_code = EXCLUDED.lobby_code,
                settings = EXCLUDED.settings,
                rules = EXCLUDED.rules,
                extra_info = EXCLUDED.extra_info,
                selected_role_id = EXCLUDED.selected_role_id
            """,
            (
                guild_id,
                channel_id,
                message_id,
                host_id,
                lobby_code,
                settings,
                rules,
                extra_info,
                selected_role_id,
            ),
        )

        connection.commit()


def get_active_lobbies(guild_id: int):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT *
            FROM active_lobbies
            WHERE guild_id = %s
            ORDER BY message_id ASC
            """,
            (guild_id,),
        )

        return cursor.fetchall()


def get_active_lobby_for_host(
    guild_id: int,
    host_id: int
):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT *
            FROM active_lobbies
            WHERE guild_id = %s AND host_id = %s
            ORDER BY message_id DESC
            LIMIT 1
            """,
            (guild_id, host_id),
        )

        return cursor.fetchone()


def delete_active_lobby(guild_id: int, message_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM active_lobbies
            WHERE guild_id = %s AND message_id = %s
            """,
            (guild_id, message_id),
        )

        connection.commit()


def delete_all_active_lobbies(guild_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM active_lobbies
            WHERE guild_id = %s
            """,
            (guild_id,),
        )

        connection.commit()

