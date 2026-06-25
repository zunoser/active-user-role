import asyncio
from datetime import UTC, datetime, timedelta
from typing import AsyncIterator

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


async def all_history(
    guild: discord.Guild,
    since: datetime,
) -> AsyncIterator[discord.Message]:
    channels = [
        *guild.text_channels,
        *guild.voice_channels,
        *[thread for channel in guild.text_channels for thread in channel.threads],
    ]

    for channel in channels:
        if not channel.permissions_for(guild.me).read_message_history:
            continue
        async for message in channel.history(after=since, limit=None):
            yield message


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
        recent_messages = [message async for message in all_history(guild, since)]
        active_user_ids = {
            message.author.id for message in recent_messages if not message.author.bot
        }
        current_role_member_ids = {member.id for member in role.members}

        diff = len(active_user_ids) - len(current_role_member_ids)
        print(f"[INFO] Messages in the last: {len(recent_messages)}")
        print(f"[INFO] Active users: {len(active_user_ids)} ({diff:+})")

        for user_id in current_role_member_ids - active_user_ids:
            member = guild.get_member(user_id)
            if member is None:
                print(f"[WARN] Member {user_id} not found")
            else:
                reason = f"No activity in the last {settings.active_lookback_days} days"
                await member.remove_roles(role, reason=reason)

        for user_id in active_user_ids - current_role_member_ids:
            member = guild.get_member(user_id)
            if member is None:
                print(f"[WARN] Member {user_id} not found")
            else:
                reason = f"Active in the last {settings.active_lookback_days} days"
                await member.add_roles(role, reason=reason)


if __name__ == "__main__":
    asyncio.run(main())
