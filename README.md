# Personal AI Laptop Agent + Telegram Bridge

This app exposes a local API (`POST /command`) for executing registered laptop commands, plus a Telegram bot bridge that forwards Telegram messages to that endpoint and sends the response back to the chat. Unknown commands are routed through the LLM planner to produce a validated multi-step plan.

## What you get

- FastAPI server with command endpoint
- API key protection via `x-api-key`
- Telegram long-polling bridge (`python -m agent.telegram_bot`)
- Command alias support (for example `open chrome`, `volume up`, `volume down`)
- LLM planning layer for strict natural-language → JSON planning

## 1) Prerequisites

- Python 3.10+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## 2) Install and set up locally

```bash
cd /path/to/personal-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Configure environment variables

You can copy `.env.example` into your shell environment or export values directly.

```bash
export API_KEY="change-me"
export DEFAULT_DIRECTORY="$HOME"
export LOG_LEVEL="INFO"

# Telegram integration
export TELEGRAM_BOT_TOKEN="123456789:your-telegram-bot-token"
export TELEGRAM_COMMAND_URL="http://127.0.0.1:8000/command"

# LLM planner
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4.1-mini"
```

> `TELEGRAM_COMMAND_URL` should point to the same API server instance you start below.

## 4) Start the API server

In terminal 1:

```bash
source .venv/bin/activate
uvicorn agent.main:app --host 0.0.0.0 --port 8000
```

Quick sanity check:

```bash
curl http://127.0.0.1:8000/health
```

## 5) Start the Telegram bridge

In terminal 2:

```bash
source .venv/bin/activate
python -m agent.telegram_bot
```

The bridge continuously:
1. Reads new Telegram messages via `getUpdates`.
2. Sends each message text to your `/command` endpoint as:
   ```json
   { "command": "<telegram text>", "args": {} }
   ```
3. Sends the endpoint response back to the same Telegram chat.

## 6) Test with your Telegram bot

1. Open Telegram and start a chat with your bot.
2. Send one of these messages:
   - `open_chrome`
   - `open vscode`
   - `volume up`
   - `volume down`
   - `list_files`
   - `Open Chrome and search youtube for Hanuman Chalisa`
3. You should receive a reply with status/message/data from `/command`.

## Optional: Test `/command` directly with curl

```bash
curl -X POST http://127.0.0.1:8000/command \
  -H "Content-Type: application/json" \
  -H "x-api-key: change-me" \
  -d '{"command":"list_files","args":{"directory":"/tmp"}}'
```

## Troubleshooting

- **401 Missing x-api-key / 403 Invalid API key**: Ensure `API_KEY` matches what the Telegram bridge uses.
- **Telegram bridge does not respond**: Confirm `TELEGRAM_BOT_TOKEN` is valid and the bridge process is running.
- **No command result**: Check API server logs for command execution errors.
- **Cannot execute OS-specific commands**: Verify the target app exists on your laptop (for example Chrome/VS Code).
- **Linux volume command fails**: Install at least one supported tool: `pactl` (PipeWire/PulseAudio) or `amixer` (ALSA).

## Project structure

```text
agent/
  api/
    routes.py
  commands/
    registry.py
    system_commands.py
  core/
    config.py
    security.py
  services/
    executor.py
    llm_planner.py
    prompt_templates.py
    validation.py
  main.py
  telegram_bot.py
```
