import discord
from discord import app_commands
from ..config import *
from ..bot_instance import bot
from ..database import *
from ..helpers import *
from ..views.lobby_views import *

# ==================================================
# SLASH COMMANDS
# ==================================================

@bot.tree.command(
    name="host",
    description="Post your Among Us lobby",
)
async def host(
    interaction: discord.Interaction
):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command must be used inside a server.",
            ephemeral=True,
        )

        return

    saved_layout = get_saved_layout(
        interaction.user.id,
        interaction.guild.id,
    )

    saved_role_id = (
        saved_layout["ping_role_id"]
        if saved_layout
        else ROLE_OPTIONS["role_one"]
    )

    view = RoleSelectionView(
        author_id=interaction.user.id,
        guild_id=interaction.guild.id,
        channel_id=interaction.channel_id,
        saved_role_id=saved_role_id,
        allow_test=(
            isinstance(interaction.user, discord.Member)
            and interaction.user.guild_permissions.administrator
        ),
    )

    await interaction.response.send_message(
        content=(
            "Choose the role you want to ping.\n"
            "Your previous choice is selected automatically."
        ),
        view=view,
        ephemeral=True,
    )


@bot.tree.command(
    name="lobbies",
    description="Show all active Among Us lobbies",
)
async def lobbies(
    interaction: discord.Interaction
):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command must be used inside a server.",
            ephemeral=True,
        )

        return

    active_lobbies = get_active_lobbies(
        interaction.guild.id
    )

    if not active_lobbies:
        await interaction.response.send_message(
            "There are currently no active lobbies.",
            ephemeral=True,
        )

        return

    embed = discord.Embed(
        title="🎮 Active Among Us Lobbies",
        color=discord.Color.blurple(),
    )

    for lobby in active_lobbies:
        channel = interaction.guild.get_channel(
            lobby["channel_id"]
        )

        channel_text = (
            channel.mention
            if channel
            else "Unknown channel"
        )

        embed.add_field(
            name=f"Lobby hosted by <@{lobby['host_id']}>",
            value=(
                f"**Code:** `{lobby['lobby_code']}`\n"
                f"**Channel:** {channel_text}\n"
                f"**Message:** [Jump to lobby]"
                f"(https://discord.com/channels/"
                f"{interaction.guild.id}/"
                f"{lobby['channel_id']}/"
                f"{lobby['message_id']})"
            ),
            inline=False,
        )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="editlobby",
    description="Edit your active lobby announcement",
)
async def editlobby(
    interaction: discord.Interaction
):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command must be used inside a server.",
            ephemeral=True,
        )

        return

    lobby = get_active_lobby_for_host(
        interaction.guild.id,
        interaction.user.id,
    )

    if not lobby:
        await interaction.response.send_message(
            "You do not have an active lobby to edit.",
            ephemeral=True,
        )

        return

    host_member = interaction.guild.get_member(
        interaction.user.id
    )

    if host_member is None:
        host_member = interaction.user

    await interaction.response.send_modal(
        EditLobbyModal(
            lobby=lobby,
            host=host_member,
        )
    )


@bot.tree.command(
    name="bump",
    description="Refresh and repost your active lobby",
)
async def bump(
    interaction: discord.Interaction
):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command must be used inside a server.",
            ephemeral=True,
        )

        return

    lobby = get_active_lobby_for_host(
        interaction.guild.id,
        interaction.user.id,
    )

    if not lobby:
        await interaction.response.send_message(
            "You do not have an active lobby to bump.",
            ephemeral=True,
        )

        return

    channel = interaction.guild.get_channel(
        lobby["channel_id"]
    )

    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "I couldn't find the lobby's channel.",
            ephemeral=True,
        )

        return

    try:
        old_message = await channel.fetch_message(
            lobby["message_id"]
        )
    except discord.NotFound:
        delete_active_lobby(
            interaction.guild.id,
            lobby["message_id"],
        )

        await interaction.response.send_message(
            "Your old lobby announcement no longer exists.",
            ephemeral=True,
        )

        return

    try:
        await old_message.delete()
    except discord.NotFound:
        pass

    host_member = interaction.guild.get_member(
        lobby["host_id"]
    )

    if host_member is None:
        host_member = interaction.user

    embed = build_lobby_embed(
        host=host_member,
        lobby_code=lobby["lobby_code"],
        settings=lobby["settings"],
        rules=lobby["rules"],
        extra_info=lobby["extra_info"],
    )

    selected_role_id = lobby["selected_role_id"]

    if selected_role_id == 0:
        announcement_content = "🧪 **Test lobby announcement — no role ping sent.**"
        allowed_mentions = discord.AllowedMentions.none()
    else:
        announcement_content = get_role_mention(selected_role_id)
        allowed_mentions = discord.AllowedMentions(
            roles=True,
            users=False,
            everyone=False,
        )

    new_message = await channel.send(
        content=announcement_content,
        embed=embed,
        allowed_mentions=allowed_mentions,
    )

    delete_active_lobby(
        interaction.guild.id,
        lobby["message_id"],
    )

    save_active_lobby(
        guild_id=interaction.guild.id,
        channel_id=lobby["channel_id"],
        message_id=new_message.id,
        host_id=lobby["host_id"],
        lobby_code=lobby["lobby_code"],
        settings=lobby["settings"],
        rules=lobby["rules"],
        extra_info=lobby["extra_info"],
        selected_role_id=lobby["selected_role_id"],
    )

    await new_message.edit(
        view=LobbyAnnouncementView(
            host_id=lobby["host_id"],
            guild_id=interaction.guild.id,
            message_id=new_message.id,
        )
    )

    await interaction.response.send_message(
        "Your lobby has been bumped.",
        ephemeral=True,
    )


@bot.tree.command(
    name="help",
    description="Show the bot's commands",
)
async def help_command(
    interaction: discord.Interaction
):
    embed = discord.Embed(
        title="🎮 Among Us Bot Help",
        description="Here are the available commands:",
        color=discord.Color.blurple(),
    )

    embed.add_field(
        name="Lobby Commands",
        value=(
            "`/host` — Post a new lobby\n"
            "`/lobbies` — Show active lobbies\n"
            "`/editlobby` — Edit your lobby\n"
            "`/bump` — Refresh your lobby\n"
            "`/clearlobbies` — Remove all active lobbies"
        ),
        inline=False,
    )

    embed.add_field(
        name="Queue Commands",
        value=(
            "`/queue` — Join the ping queue\n"
            "`/leavequeue` — Leave the ping queue\n"
            "`/queuelist` — View the current queue\n"
            "Lobby hosts can press **Ping Queue** "
            "to notify everyone waiting."
        ),
        inline=False,
    )

    embed.add_field(
        name="Server Commands",
        value=(
            "`/setrules` — Set default lobby rules\n"
            "`/stats` — View your hosting stats\n"
            "`/leaderboard` — View top hosts\n"
            "`/resetlobbyinfo` — Reset saved lobby information"
        ),
        inline=False,
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )


@bot.tree.command(
    name="setrules",
    description="Set the server's default lobby rules",
)
@app_commands.describe(
    rules="The default rules used for new lobbies"
)
async def setrules(
    interaction: discord.Interaction,
    rules: str,
):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command must be used inside a server.",
            ephemeral=True,
        )

        return

    if not is_admin(interaction):
        await interaction.response.send_message(
            "Only server administrators can set default rules.",
            ephemeral=True,
        )

        return

    save_default_rules(
        interaction.guild.id,
        rules,
    )

    await interaction.response.send_message(
        "The server's default lobby rules have been saved.",
        ephemeral=True,
    )


@bot.tree.command(
    name="stats",
    description="Show your lobby hosting stats",
)
async def stats(
    interaction: discord.Interaction
):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command must be used inside a server.",
            ephemeral=True,
        )

        return

    count = get_user_host_count(
        interaction.user.id,
        interaction.guild.id,
    )

    await interaction.response.send_message(
        f"🎮 You have hosted **{count}** lobby"
        f"{'' if count == 1 else 's'} "
        f"in this server.",
        ephemeral=True,
    )


@bot.tree.command(
    name="leaderboard",
    description="Show the server's top lobby hosts",
)
async def leaderboard(
    interaction: discord.Interaction
):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command must be used inside a server.",
            ephemeral=True,
        )

        return

    rows = get_leaderboard(
        interaction.guild.id
    )

    if not rows:
        await interaction.response.send_message(
            "No one has hosted a lobby yet.",
            ephemeral=True,
        )

        return

    description = ""

    for index, row in enumerate(rows, start=1):
        description += (
            f"**{index}.** <@{row['user_id']}> — "
            f"**{row['hosted_count']}** lobbies\n"
        )

    embed = discord.Embed(
        title="🏆 Lobby Host Leaderboard",
        description=description,
        color=discord.Color.gold(),
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="clearlobbies",
    description="Remove all active lobby announcements",
)
async def clearlobbies(
    interaction: discord.Interaction
):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command must be used inside a server.",
            ephemeral=True,
        )

        return

    if not is_admin(interaction):
        await interaction.response.send_message(
            "Only server administrators can clear lobbies.",
            ephemeral=True,
        )

        return

    active_lobbies = get_active_lobbies(
        interaction.guild.id
    )

    deleted_count = 0

    for lobby in active_lobbies:
        channel = interaction.guild.get_channel(
            lobby["channel_id"]
        )

        if isinstance(channel, discord.TextChannel):
            try:
                message = await channel.fetch_message(
                    lobby["message_id"]
                )

                await message.delete()
                deleted_count += 1

            except discord.NotFound:
                pass

            except discord.Forbidden:
                pass

    delete_all_active_lobbies(
        interaction.guild.id
    )

    await interaction.response.send_message(
        f"Cleared **{deleted_count}** active lobby announcement"
        f"{'' if deleted_count == 1 else 's'}.",
        ephemeral=True,
    )


@bot.tree.command(
    name="resetlobbyinfo",
    description="Reset your saved lobby information",
)
async def resetlobbyinfo(
    interaction: discord.Interaction
):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command must be used inside a server.",
            ephemeral=True,
        )

        return

    delete_layout(
        user_id=interaction.user.id,
        guild_id=interaction.guild.id,
    )

    await interaction.response.send_message(
        "Your saved lobby information has been reset.",
        ephemeral=True,
    )


@bot.tree.command(
    name="queue",
    description="Join the Among Us ping queue",
)
async def queue(
    interaction: discord.Interaction
):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command must be used inside a server.",
            ephemeral=True,
        )

        return

    added = add_to_queue(
        interaction.user.id,
        interaction.guild.id,
    )

    if added:
        position = len(
            get_queue(interaction.guild.id)
        )

        await interaction.response.send_message(
            f"✅ You joined the ping queue at position **{position}**.",
            ephemeral=True,
        )

    else:
        await interaction.response.send_message(
            "You are already in the ping queue.",
            ephemeral=True,
        )


@bot.tree.command(
    name="leavequeue",
    description="Leave the Among Us ping queue",
)
async def leavequeue(
    interaction: discord.Interaction
):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command must be used inside a server.",
            ephemeral=True,
        )

        return

    removed = remove_from_queue(
        interaction.user.id,
        interaction.guild.id,
    )

    if removed:
        await interaction.response.send_message(
            "You left the ping queue.",
            ephemeral=True,
        )

    else:
        await interaction.response.send_message(
            "You are not currently in the ping queue.",
            ephemeral=True,
        )


@bot.tree.command(
    name="queuelist",
    description="Show everyone in the ping queue",
)
async def queuelist(
    interaction: discord.Interaction
):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command must be used inside a server.",
            ephemeral=True,
        )

        return

    queued_users = get_queue(
        interaction.guild.id
    )

    if not queued_users:
        await interaction.response.send_message(
            "The ping queue is currently empty.",
            ephemeral=True,
        )

        return

    description = ""

    for index, user_id in enumerate(
        queued_users,
        start=1,
    ):
        description += (
            f"**{index}.** <@{user_id}>\n"
        )

    embed = discord.Embed(
        title="📢 Among Us Ping Queue",
        description=description,
        color=discord.Color.blurple(),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

