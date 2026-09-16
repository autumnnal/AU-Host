from typing import Optional
import discord
from .config import ROLE_OPTIONS

# ==================================================
# HELPER FUNCTIONS
# ==================================================

def get_role_mention(role_id: Optional[int]) -> str:
    if role_id is None or role_id == 0:
        return ""
    return f"||<@&{role_id}>||"


def clean_text(
    value: str,
    fallback: str = "Not provided"
) -> str:
    value = value.strip()

    if not value:
        return fallback

    return value


def build_lobby_embed(
    host: discord.Member,
    lobby_code: str,
    settings: str,
    rules: str,
    extra_info: str,
) -> discord.Embed:
    embed = discord.Embed(
        title="🎮 Among Us Lobby",
        description=(
            "A new lobby is being hosted!\n"
            "Check the information below before joining."
        ),
        color=discord.Color.from_rgb(88, 101, 242),
        timestamp=discord.utils.utcnow(),
    )

    embed.add_field(
        name="🔑 Lobby Code",
        value=f"```{clean_text(lobby_code)}```",
        inline=False,
    )

    embed.add_field(
        name="⚙️ Settings",
        value=clean_text(settings),
        inline=False,
    )

    embed.add_field(
        name="📜 Rules",
        value=clean_text(rules),
        inline=False,
    )

    if extra_info.strip():
        embed.add_field(
            name="ℹ️ Additional Information",
            value=extra_info.strip(),
            inline=False,
        )

    embed.set_footer(
        text=f"Hosted by {host.display_name}",
        icon_url=host.display_avatar.url,
    )

    return embed


def is_admin(interaction: discord.Interaction) -> bool:
    return (
        isinstance(interaction.user, discord.Member)
        and interaction.user.guild_permissions.administrator
    )


