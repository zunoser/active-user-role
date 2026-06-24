# active-user-role

Discord.py bot that assigns an existing active role to users who posted in the
target server within the last 14 days.

Activity is detected from messages in:

- Text channels
- Voice channel text chats

The bot runs once immediately after startup and exits normally after processing
finishes. Run it every day at midnight with GitHub Actions or another scheduler.

## Setup

1. Replace the placeholders in `main.py`:
   - `TARGET_GUILD_ID`
   - `ACTIVE_ROLE_ID`
2. Set the bot token as an environment variable. For GitHub Actions, store it
   as a repository secret and pass it through `env`.

```sh
export DISCORD_TOKEN='your-bot-token'
```

3. Run the bot:

```sh
uv run python main.py
```

The bot intentionally does not write progress logs, counts, channel names, user
IDs, role IDs, or exception details to stdout/stderr.

## Checks

```sh
uv run ruff format --check .
uv run ruff check .
uv run ty check .
pnpm run format:check
```

## GitHub Actions

The workflow is defined in `.github/workflows/active-role.yml`.

CI checks are defined in `.github/workflows/ci.yml`.

Set this repository secret:

- `DISCORD_TOKEN`: Discord bot token

The workflow runs at `00:00 JST` every day. GitHub Actions schedules are written
in UTC, so the cron expression is `0 15 * * *`.

You can also run it manually from the Actions tab with `workflow_dispatch`.

## Discord Requirements

The bot needs:

- Server Members Intent enabled in the Discord Developer Portal
- Permission to view channels and read message history
- Permission to manage roles
- The bot role must be higher than the active role in the server role hierarchy

The active role must already exist. This bot intentionally does not create a
fallback role when `ACTIVE_ROLE_ID` is missing.
