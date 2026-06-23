import os
from datetime import UTC, datetime, timedelta

import discord


TARGET_GUILD_ID = 1422820164147085316
ACTIVE_ROLE_ID = 1518619420942143498

ACTIVE_LOOKBACK_DAYS = 14


class ActiveRoleClient(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        super().__init__(intents=intents)
        self._task_started = False
        self.failed = False

    async def on_ready(self) -> None:
        if self._task_started:
            return

        self._task_started = True
        self.loop.create_task(self._run_once())

    async def _run_once(self) -> None:
        try:
            await self.assign_active_role()
        except Exception:
            self.failed = True
        finally:
            await self.close()

    async def assign_active_role(self) -> None:
        guild = self.get_guild(TARGET_GUILD_ID)
        if guild is None:
            guild = await self.fetch_guild(TARGET_GUILD_ID)

        role = guild.get_role(ACTIVE_ROLE_ID)
        if role is None:
            self.failed = True
            return

        since = datetime.now(UTC) - timedelta(days=ACTIVE_LOOKBACK_DAYS)
        active_user_ids = await self.collect_active_user_ids(guild, since)

        for member in role.members:
            if member.id not in active_user_ids and not member.bot:
                try:
                    await member.remove_roles(role, reason=f"Not active within the last {ACTIVE_LOOKBACK_DAYS} days")
                except discord.Forbidden:
                    self.failed = True

        for user_id in sorted(active_user_ids):
            try:
                member = guild.get_member(user_id) or await guild.fetch_member(user_id)
            except discord.NotFound:
                continue

            if member.bot or role in member.roles:
                continue

            try:
                await member.add_roles(role, reason=f"Active within the last {ACTIVE_LOOKBACK_DAYS} days")
            except discord.Forbidden:
                self.failed = True

    async def collect_active_user_ids(
        self,
        guild: discord.Guild,
        since: datetime,
    ) -> set[int]:
        active_user_ids: set[int] = set()
        channels = [*guild.text_channels, *guild.voice_channels]

        for channel in channels:
            try:
                async for message in channel.history(after=since, oldest_first=False):
                    if message.author.bot:
                        continue
                    active_user_ids.add(message.author.id)
            except (discord.Forbidden, discord.HTTPException):
                continue

        return active_user_ids


def main() -> None:
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit(1)

    client = ActiveRoleClient()
    try:
        client.run(token, log_handler=None)
    except Exception:
        raise SystemExit(1) from None

    if client.failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
