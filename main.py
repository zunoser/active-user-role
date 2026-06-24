import asyncio
from datetime import UTC, datetime, timedelta

import discord
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    discord_token: SecretStr
    target_guild_id: int = 1422820164147085316
    active_role_id: int = 1518619420942143498
    active_lookback_days: int = 14

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


async def collect_active_user_ids(guild: discord.Guild, since: datetime) -> set[int]:
    active_user_ids: set[int] = set()
    channels = [*guild.text_channels, *guild.voice_channels]

    for channel in channels:
        if not channel.permissions_for(guild.me).read_message_history:
            continue
        async for message in channel.history(after=since, oldest_first=False):
            active_user_ids.add(message.author.id)

    return active_user_ids


async def main() -> None:
    settings = Settings()

    intents = discord.Intents.default()
    intents.guilds = True
    intents.members = True

    async with discord.Client(intents=intents) as client:
        asyncio.create_task(client.start(settings.discord_token.get_secret_value()))
        await client.wait_until_ready()

        guild = client.get_guild(settings.target_guild_id)
        if guild is None:
            raise RuntimeError(f"Guild {settings.target_guild_id} not found")

        role = guild.get_role(settings.active_role_id)
        if role is None:
            raise RuntimeError(f"Role {settings.active_role_id} not found")

        since = datetime.now(UTC) - timedelta(days=settings.active_lookback_days)
        bot_ids = {member.id for member in guild.members if member.bot}
        active_ids = await collect_active_user_ids(guild, since) - bot_ids
        current_ids = {member.id for member in role.members}

        for user_id in current_ids - active_ids:
            member = guild.get_member(user_id)
            if member is not None:
                reason = f"No activity in the last {settings.active_lookback_days} days"
                await member.remove_roles(role, reason=reason)

        for user_id in active_ids - current_ids:
            member = guild.get_member(user_id)
            if member is not None:
                reason = f"Active in the last {settings.active_lookback_days} days"
                await member.add_roles(role, reason=reason)


if __name__ == "__main__":
    asyncio.run(main())
