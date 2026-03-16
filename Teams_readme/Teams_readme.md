# Teams Bot Setup

Use this guide when you want ArgusBot to be controlled from Microsoft Teams through a Bot Framework bot.

## What ArgusBot Needs

Required:

- Teams bot `app id`
- Teams bot `app password` / client secret

Optional but useful when you already know them:

- `conversation id`
- `service URL`
- `tenant id`

If you do not prefill `conversation id` and `service URL`, ArgusBot can learn them automatically from the first inbound Teams message and persist them into `.argusbot/teams_reference.json`.

## Listener Endpoint

ArgusBot exposes a local Teams callback listener with these defaults:

- host: `0.0.0.0`
- port: `3978`
- path: `/api/messages`

Default local URL:

```text
http://127.0.0.1:3978/api/messages
```

Teams requires a public HTTPS messaging endpoint, so in practice you normally put ArgusBot behind one of these:

- a reverse proxy that terminates HTTPS
- a tunnel such as `ngrok`, `cloudflared`, or similar
- a public VM/container ingress

Then configure the bot messaging endpoint in Azure / Teams to point to:

```text
https://<your-public-host>/api/messages
```

## `argusbot init`

The simplest path is:

```bash
argusbot init
```

Then choose `Teams` as the control channel and provide:

- `Teams app id`
- `Teams app password/secret`
- optionally `conversation id`
- optionally `service URL`
- optionally `tenant id`

After startup:

1. Make sure the public HTTPS endpoint is reachable.
2. Send the bot one message in Teams.
3. ArgusBot will persist the learned conversation reference.
4. From then on, daemon replies and child-run notifications can target the same Teams conversation.

## Direct CLI

Standalone run:

```bash
argusbot-run \
  --teams-app-id "$TEAMS_APP_ID" \
  --teams-app-password "$TEAMS_APP_PASSWORD" \
  --teams-endpoint-host 0.0.0.0 \
  --teams-endpoint-port 3978 \
  --teams-endpoint-path /api/messages \
  "your objective"
```

If you already know the proactive-routing coordinates:

```bash
argusbot-run \
  --teams-app-id "$TEAMS_APP_ID" \
  --teams-app-password "$TEAMS_APP_PASSWORD" \
  --teams-conversation-id "$TEAMS_CONVERSATION_ID" \
  --teams-service-url "$TEAMS_SERVICE_URL" \
  --teams-tenant-id "$TEAMS_TENANT_ID" \
  "your objective"
```

Daemon mode:

```bash
argusbot-daemon \
  --teams-app-id "$TEAMS_APP_ID" \
  --teams-app-password "$TEAMS_APP_PASSWORD" \
  --teams-endpoint-host 0.0.0.0 \
  --teams-endpoint-port 3978 \
  --teams-endpoint-path /api/messages
```

## Commands

Teams supports the same text commands as the Telegram daemon flow:

- `/run <objective>`
- `/inject <instruction>`
- `/status`
- `/stop`
- `/mode <off|auto|record>`
- `/plan <direction>`
- `/review <criteria>`
- `/btw <question>`
- plain text while idle -> treated as `/run`
- plain text while running -> treated as `/inject`

## Notes

- The daemon stores the Teams conversation reference in `teams_reference.json` so child runs can reuse it.
- Teams attachment delivery depends on Bot Framework attachment acceptance. When inline attachment delivery is rejected, ArgusBot falls back to a text notice with the local file path.
- Put the callback listener behind your own HTTPS endpoint or tunnel and apply your normal ingress controls before exposing it on the public internet.
- If you run multiple channels at once, terminal control continues to work through `argusbot-daemon-ctl`.
