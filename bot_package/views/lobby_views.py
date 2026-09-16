from typing import Optional
import discord
from ..config import ROLE_OPTIONS
from ..bot_instance import bot
from ..database import *
from ..helpers import *

# ==================================================

class PingRoleSelect(discord.ui.Select):

    def __init__(
        self,
        saved_role_id: Optional[int] = None,
        allow_test: bool = False,
    ):
        options = [
            discord.SelectOption(
                label="Casual Game Ping",
                description="Ping the casual game role",
                value="role_one",
                emoji="📢",
                default=(
                    saved_role_id == ROLE_OPTIONS["role_one"]
                ),
            ),
            discord.SelectOption(
                label="Competitive Game Ping",
                description="Ping the competitive game role",
                value="role_two",
                emoji="📣",
                default=(
                    saved_role_id == ROLE_OPTIONS["role_two"]
                ),
            ),
        ]

        if allow_test:
            options.append(discord.SelectOption(
                label="Test",
                description="Admin-only test announcement with no ping",
                value="test",
                emoji="🧪",
                default=saved_role_id is None,
            ))

        super().__init__(
            placeholder="Choose which role to ping",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):
        if self.values[0] == "test":
            self.view.selected_role_id = 0
            self.view.selected_ping_value = "test"
            selected_text = "🧪 Test (no one will be pinged)"
        else:
            self.view.selected_role_id = ROLE_OPTIONS[self.values[0]]
            self.view.selected_ping_value = self.values[0]
            selected_text = f"<@&{self.view.selected_role_id}>"

        # Update the option defaults so Discord keeps the newly selected
        # option displayed instead of reverting to the previous choice.
        for option in self.options:
            option.default = option.value == self.values[0]

        await interaction.response.edit_message(
            content=(
                f"Selected option: {selected_text}\n\n"
                "Click **Open Lobby Form** when ready."
            ),
            view=self.view,
        )


class RoleSelectionView(discord.ui.View):

    def __init__(
        self,
        author_id: int,
        guild_id: int,
        channel_id: int,
        saved_role_id: Optional[int] = None,
        allow_test: bool = False,
    ):
        super().__init__(timeout=300)

        self.author_id = author_id
        self.guild_id = guild_id
        self.channel_id = channel_id

        if saved_role_id == 0 and allow_test:
            self.selected_role_id = 0
            self.selected_ping_value = "test"
        elif saved_role_id in ROLE_OPTIONS.values():
            self.selected_role_id = saved_role_id
            self.selected_ping_value = next(
                key for key, value in ROLE_OPTIONS.items()
                if value == saved_role_id
            )
        else:
            self.selected_role_id = ROLE_OPTIONS["role_one"]
            self.selected_ping_value = "role_one"

        self.add_item(
            PingRoleSelect(saved_role_id, allow_test=allow_test)
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This lobby setup belongs to someone else.",
                ephemeral=True,
            )

            return False

        return True

    @discord.ui.button(
        label="Open Lobby Form",
        style=discord.ButtonStyle.primary,
        emoji="📝",
    )
    async def open_form(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        saved_layout = get_saved_layout(
            self.author_id,
            self.guild_id,
        )

        modal = LobbyModal(
            author_id=self.author_id,
            guild_id=self.guild_id,
            channel_id=self.channel_id,
            selected_role_id=self.selected_role_id,
            saved_layout=saved_layout,
        )

        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.edit_message(
            content="Lobby announcement cancelled.",
            view=None,
        )


# ==================================================
# LOBBY FORM
# ==================================================

class LobbyModal(
    discord.ui.Modal,
    title="Create Among Us Lobby"
):

    lobby_code = discord.ui.TextInput(
        label="Lobby Code",
        placeholder="Example: ABCD12",
        required=True,
        max_length=20,
        style=discord.TextStyle.short,
    )

    settings = discord.ui.TextInput(
        label="Settings",
        placeholder=(
            "Put your lobby settings here.\n"
            "Example:\n"
            "Map: The Skeld\n"
            "Confirm Ejects: On"
        ),
        required=False,
        max_length=2000,
        style=discord.TextStyle.paragraph,
    )

    rules = discord.ui.TextInput(
        label="Rules",
        placeholder=(
            "Put your lobby rules here.\n"
            "Example:\n"
            "No cheating\n"
            "Be respectful"
        ),
        required=False,
        max_length=2000,
        style=discord.TextStyle.paragraph,
    )

    extra_info = discord.ui.TextInput(
        label="Additional Information",
        placeholder=(
            "Optional information, voice chat details, etc."
        ),
        required=False,
        max_length=1000,
        style=discord.TextStyle.paragraph,
    )

    def __init__(
        self,
        author_id: int,
        guild_id: int,
        channel_id: int,
        selected_role_id: int,
        saved_layout: Optional[dict] = None,
    ):
        super().__init__()

        self.author_id = author_id
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.selected_role_id = selected_role_id

        if saved_layout:
            self.settings.default = saved_layout["settings"]
            self.rules.default = saved_layout["rules"]
            self.extra_info.default = saved_layout["extra_info"]

        elif get_default_rules(guild_id):
            self.rules.default = get_default_rules(guild_id)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command must be used inside a server.",
                ephemeral=True,
            )

            return

        host = interaction.guild.get_member(
            self.author_id
        )

        if host is None:
            host = interaction.user

        embed = build_lobby_embed(
            host=host,
            lobby_code=self.lobby_code.value,
            settings=self.settings.value,
            rules=self.rules.value,
            extra_info=self.extra_info.value,
        )

        preview_view = AnnouncementPreviewView(
            author_id=self.author_id,
            guild_id=self.guild_id,
            channel_id=self.channel_id,
            lobby_code=self.lobby_code.value,
            settings=self.settings.value,
            rules=self.rules.value,
            extra_info=self.extra_info.value,
            selected_role_id=self.selected_role_id,
            embed=embed,
        )

        if self.selected_role_id == 0:
            preview_ping = "🧪 **Ping: Test** — no role will be pinged"
        elif self.selected_role_id == ROLE_OPTIONS["role_one"]:
            preview_ping = "📢 **Ping: Casual Game Ping**"
        elif self.selected_role_id == ROLE_OPTIONS["role_two"]:
            preview_ping = "📣 **Ping: Competitive Game Ping**"
        else:
            preview_ping = "🔔 **Ping: Unknown selection**"

        await interaction.response.send_message(
            content=(
                "Here is your private preview.\n"
                f"{preview_ping}\n\n"
                "Click **Host Lobby** to post your lobby "
                "or press **Cancel** to cancel this action."
            ),
            embed=embed,
            view=preview_view,
            ephemeral=True,
        )


# ==================================================
# QUEUE PING MESSAGE BUTTONS
# ==================================================

class QueuePingView(discord.ui.View):

    def __init__(self, host_id: int):
        super().__init__(timeout=None)
        self.host_id = host_id

    async def can_manage(self, interaction: discord.Interaction) -> bool:
        return (
            interaction.user.id == self.host_id
            or is_admin(interaction)
        )

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
    )
    async def close_ping(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not await self.can_manage(interaction):
            await interaction.response.send_message(
                "Only the lobby host or a server administrator "
                "can close this queue ping.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass


# ==================================================
# LOBBY ANNOUNCEMENT BUTTONS
# ==================================================

class LobbyAnnouncementView(discord.ui.View):

    def __init__(
        self,
        host_id: int,
        guild_id: int,
        message_id: int,
    ):
        super().__init__(timeout=None)

        self.host_id = host_id
        self.guild_id = guild_id
        self.message_id = message_id

    async def can_manage(
        self,
        interaction: discord.Interaction
    ) -> bool:
        return (
            interaction.user.id == self.host_id
            or is_admin(interaction)
        )

    @discord.ui.button(
        label="Ping Queue",
        style=discord.ButtonStyle.primary,
        emoji="📢",
    )
    async def ping_queue(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not await self.can_manage(interaction):
            await interaction.response.send_message(
                "Only the lobby host or a server administrator "
                "can ping the queue.",
                ephemeral=True,
            )

            return

        queued_users = get_queue(self.guild_id)

        if not queued_users:
            await interaction.response.send_message(
                "The ping queue is currently empty.",
                ephemeral=True,
            )

            return

        mentions = " ".join(
            f"<@{user_id}>"
            for user_id in queued_users
        )

        clear_queue(self.guild_id)

        await interaction.response.send_message(
            content=(
                f"🎮 **The lobby is open!**\n"
                f"{mentions}"
            ),
            view=QueuePingView(host_id=self.host_id),
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=False,
                everyone=False,
            ),
        )

    @discord.ui.button(
        label="Close Lobby",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
    )
    async def close_lobby(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not await self.can_manage(interaction):
            await interaction.response.send_message(
                "Only the lobby host or a server administrator "
                "can close this lobby.",
                ephemeral=True,
            )

            return

        delete_active_lobby(
            self.guild_id,
            self.message_id,
        )

        await interaction.response.defer()

        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass


# ==================================================
# PREVIEW AND SEND BUTTONS
# ==================================================

class AnnouncementPreviewView(discord.ui.View):

    def __init__(
        self,
        author_id: int,
        guild_id: int,
        channel_id: int,
        lobby_code: str,
        settings: str,
        rules: str,
        extra_info: str,
        selected_role_id: int,
        embed: discord.Embed,
    ):
        super().__init__(timeout=300)

        self.author_id = author_id
        self.guild_id = guild_id
        self.channel_id = channel_id

        self.lobby_code = lobby_code
        self.settings = settings
        self.rules = rules
        self.extra_info = extra_info

        self.selected_role_id = selected_role_id
        self.embed = embed

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This preview belongs to someone else.",
                ephemeral=True,
            )

            return False

        return True

    @discord.ui.button(
        label="Host Lobby",
        style=discord.ButtonStyle.success,
        emoji="📤",
    )
    async def send_announcement(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        # Acknowledge the interaction immediately. Discord only allows
        # a few seconds for an interaction response.
        await interaction.response.defer(ephemeral=True)

        try:
            if interaction.guild is None:
                await interaction.edit_original_response(
                    content="This action must be used inside a server.",
                    embed=None,
                    view=None,
                )
                return

            channel = interaction.guild.get_channel(self.channel_id)

            if channel is None:
                await interaction.edit_original_response(
                    content=(
                        "I couldn't find the original channel. "
                        "The announcement was not sent."
                    ),
                    embed=None,
                    view=None,
                )
                return

            if not isinstance(channel, discord.TextChannel):
                await interaction.edit_original_response(
                    content="The original channel is not a text channel.",
                    embed=None,
                    view=None,
                )
                return

            save_layout(
                user_id=self.author_id,
                guild_id=self.guild_id,
                settings=self.settings,
                rules=self.rules,
                extra_info=self.extra_info,
                ping_role_id=self.selected_role_id,
            )

            increment_host_stats(self.author_id, self.guild_id)

            if self.selected_role_id == 0:
                announcement_content = (
                    "🧪 **Test lobby announcement — no role ping sent.**"
                )
                allowed_mentions = discord.AllowedMentions.none()
            else:
                announcement_content = get_role_mention(
                    self.selected_role_id
                )
                allowed_mentions = discord.AllowedMentions(
                    roles=True,
                    users=False,
                    everyone=False,
                )

            message = await channel.send(
                content=announcement_content,
                embed=self.embed,
                view=LobbyAnnouncementView(
                    host_id=self.author_id,
                    guild_id=self.guild_id,
                    message_id=0,
                ),
                allowed_mentions=allowed_mentions,
            )

            save_active_lobby(
                guild_id=self.guild_id,
                channel_id=self.channel_id,
                message_id=message.id,
                host_id=self.author_id,
                lobby_code=self.lobby_code,
                settings=self.settings,
                rules=self.rules,
                extra_info=self.extra_info,
                selected_role_id=self.selected_role_id,
            )

            view = LobbyAnnouncementView(
                host_id=self.author_id,
                guild_id=self.guild_id,
                message_id=message.id,
            )
            await message.edit(view=view)

            await interaction.edit_original_response(
                content="Your lobby announcement has been sent!",
                embed=None,
                view=None,
            )

        except Exception as error:
            import traceback
            traceback.print_exc()

            try:
                await interaction.edit_original_response(
                    content=(
                        "❌ **Failed to send the lobby announcement.**\n"
                        f"```{type(error).__name__}: {error}```"
                    ),
                    embed=None,
                    view=None,
                )
            except Exception:
                pass

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.edit_message(
            content="Lobby announcement cancelled.",
            embed=None,
            view=None,
        )


# ==================================================
# EDIT LOBBY MODAL
# ==================================================

class EditLobbyModal(
    discord.ui.Modal,
    title="Edit Among Us Lobby"
):

    lobby_code = discord.ui.TextInput(
        label="Lobby Code",
        required=True,
        max_length=20,
        style=discord.TextStyle.short,
    )

    settings = discord.ui.TextInput(
        label="Settings",
        required=False,
        max_length=2000,
        style=discord.TextStyle.paragraph,
    )

    rules = discord.ui.TextInput(
        label="Rules",
        required=False,
        max_length=2000,
        style=discord.TextStyle.paragraph,
    )

    extra_info = discord.ui.TextInput(
        label="Additional Information",
        required=False,
        max_length=1000,
        style=discord.TextStyle.paragraph,
    )

    def __init__(
        self,
        lobby: dict,
        host: discord.Member,
    ):
        super().__init__()

        self.lobby = lobby
        self.host = host

        self.lobby_code.default = lobby["lobby_code"]
        self.settings.default = lobby["settings"]
        self.rules.default = lobby["rules"]
        self.extra_info.default = lobby["extra_info"]

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        channel = interaction.guild.get_channel(
            self.lobby["channel_id"]
        )

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "I couldn't find the lobby's channel.",
                ephemeral=True,
            )

            return

        try:
            message = await channel.fetch_message(
                self.lobby["message_id"]
            )
        except discord.NotFound:
            delete_active_lobby(
                interaction.guild.id,
                self.lobby["message_id"],
            )

            await interaction.response.send_message(
                "That lobby announcement no longer exists.",
                ephemeral=True,
            )

            return

        embed = build_lobby_embed(
            host=self.host,
            lobby_code=self.lobby_code.value,
            settings=self.settings.value,
            rules=self.rules.value,
            extra_info=self.extra_info.value,
        )

        await message.edit(embed=embed)

        save_active_lobby(
            guild_id=interaction.guild.id,
            channel_id=self.lobby["channel_id"],
            message_id=self.lobby["message_id"],
            host_id=self.lobby["host_id"],
            lobby_code=self.lobby_code.value,
            settings=self.settings.value,
            rules=self.rules.value,
            extra_info=self.extra_info.value,
            selected_role_id=self.lobby["selected_role_id"],
        )

        await interaction.response.send_message(
            "Your lobby has been updated.",
            ephemeral=True,
        )

