# Personal AI Laptop Agent (MVP)

A production-oriented MVP for remotely controlling a laptop from a mobile client over HTTP.

## Features

- FastAPI API server with `POST /command`
- API key auth via `x-api-key`
- Command registry + executor abstraction
- OS-aware command execution (Windows/macOS/Linux)
- Structured logging for every command execution
- Graceful error handling
- Environment-based configuration
- Simple natural-language command aliasing (bonus)

## Project Structure

```text
agent/
  main.py
  api/
    routes.py
  core/
    config.py
    security.py
  commands/
    registry.py
    system_commands.py
  services/
    executor.py
```

## Supported Commands

- `open_chrome`
- `open_vscode` (falls back to Cursor if available)
- `increase_volume`
- `list_files`
- `open_file`

Natural-language aliases are supported for common phrases:
- `open chrome` → `open_chrome`
- `open vs code` / `open cursor` → `open_vscode`
- `volume up` → `increase_volume`

## Configuration

Set environment variables:

- `API_KEY` (required)
- `DEFAULT_DIRECTORY` (optional, defaults to user home)
- `LOG_LEVEL` (optional, defaults to `INFO`)

## Run

### 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Export config

```bash
export API_KEY="change-me"
export DEFAULT_DIRECTORY="$HOME"
```

### 3) Start server

```bash
uvicorn agent.main:app --host 0.0.0.0 --port 8000
```

## API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

### Execute Command

```bash
curl -X POST http://localhost:8000/command \
  -H "Content-Type: application/json" \
  -H "x-api-key: change-me" \
  -d '{
    "command": "open_chrome"
  }'
```

Example response:

```json
{
  "status": "success",
  "message": "Chrome opened",
  "data": null
}
```

### Command with Args (`list_files`)

```bash
curl -X POST http://localhost:8000/command \
  -H "Content-Type: application/json" \
  -H "x-api-key: change-me" \
  -d '{
    "command": "list_files",
    "args": {
      "directory": "/tmp"
    }
  }'
```

## Design Notes for Future Extensibility

The architecture is intentionally prepared for:
- WebSocket command streaming
- LLM-based natural language command planning
- Mobile client integration

without forcing those concerns into the MVP implementation.
