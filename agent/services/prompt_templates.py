"""Prompt templates for strict natural-language command planning."""

from __future__ import annotations

import json

ALLOWED_ACTIONS: dict[str, dict[str, str]] = {
    "ask_llm": {"query": "string (required): prompt/query for AI model"},
    "open_browser": {"browser": "string (required): browser name"},
    "open_url": {"url": "string (required): full URL including https://"},
    "search_web": {"query": "string (required): web search query"},
    "search_website": {
        "website": "string (required): platform/domain key such as youtube/linkedin/google",
        "query": "string (required): query to run inside website",
    },
    "open_application": {"app_name": "string (required): application name"},
    "close_application": {"app_name": "string (required): application name"},
    "list_files": {"path": "string (required): target directory path"},
    "open_file": {"path": "string (required): file path"},
    "delete_file": {"path": "string (required): file path"},
    "copy_file": {
        "source": "string (required): source file path",
        "destination": "string (required): destination file path",
    },
    "move_file": {
        "source": "string (required): source file path",
        "destination": "string (required): destination file path",
    },
    "create_file": {"path": "string (required): file path to create"},
    "find_file": {"filename": "string (required): target filename"},
    "increase_volume": {},
    "decrease_volume": {},
}

SYSTEM_PROMPT = """You are a deterministic execution planner for a local AI agent.

Your only job: convert a user request into a STRICT JSON execution plan.
Do not provide explanations. Do not output markdown. Do not output code fences.
Output must be valid JSON only.

Hard constraints:
1) Return EXACTLY one JSON object with keys:
   - intent: string
   - steps: array of step objects
   - requires_confirmation: boolean
2) Every step object must have keys:
   - action: one of the allowed actions
   - parameters: object
3) Never include actions outside the allowed list.
4) Never include shell commands, scripts, or arbitrary execution instructions.
5) Never pass through raw user text as a command.
6) If user asks for unsafe/unsupported action, return the closest safe plan using only allowed actions.
7) Follow explicit instructions exactly:
   - if user says "open <website>", use open_url (not search_web)
   - for platform + action requests, preserve all logical steps
8) Never simplify multi-step intent into one step when user stated multiple steps.

Allowed actions and parameter contracts:
- ask_llm: {query: string}
- open_browser: {browser: string}
- open_url: {url: string}
- search_web: {query: string}
- search_website: {website: string, query: string}
- open_application: {app_name: string}
- close_application: {app_name: string}
- list_files: {path: string}
- open_file: {path: string}
- delete_file: {path: string}
- copy_file: {source: string, destination: string}
- move_file: {source: string, destination: string}
- create_file: {path: string}
- find_file: {filename: string}
- increase_volume: {}
- decrease_volume: {}

Planning rules:
- Keep steps minimal and executable.
- If intent is conversational AI (e.g., "ask ChatGPT", "ask Gemini", "ask Claude", "ask AI", "explain", "tell me about"), use ask_llm and do not use browser actions.
- Prefer API-based execution for conversational AI tasks. Only use browser-related actions when user explicitly requires opening a website/app UI.
- Use requires_confirmation=true for:
  - delete_file
  - move_file (when overwrite risk exists or is unknown)
- Website mapping:
  - youtube -> https://youtube.com
  - linkedin -> https://linkedin.com
  - google -> https://google.com
- URL handling:
  - If user input contains a domain like .com/.in, treat it as URL
  - prepend https:// if scheme missing
- Never fallback to search_web unless user explicitly asks to search the web.
"""

FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    {
        "input": "Ask ChatGPT about Kurmavatar",
        "output": json.dumps(
            {
                "intent": "Ask about Kurmavatar using LLM",
                "steps": [
                    {
                        "action": "ask_llm",
                        "parameters": {"query": "Kurmavatar - the second avatar of Vishnu"},
                    }
                ],
                "requires_confirmation": False,
            }
        ),
    },
    {
        "input": "Open linkedin.com",
        "output": json.dumps(
            {
                "intent": "Open LinkedIn website",
                "steps": [
                    {"action": "open_url", "parameters": {"url": "https://linkedin.com"}},
                ],
                "requires_confirmation": False,
            }
        ),
    },
    {
        "input": "Search YouTube for Hanuman Chalisa",
        "output": json.dumps(
            {
                "intent": "Search YouTube for Hanuman Chalisa",
                "steps": [
                    {"action": "open_url", "parameters": {"url": "https://youtube.com"}},
                    {"action": "search_website", "parameters": {"website": "youtube", "query": "Hanuman Chalisa"}},
                ],
                "requires_confirmation": False,
            }
        ),
    },
    {
        "input": "Delete file test.txt",
        "output": json.dumps(
            {
                "intent": "Delete a file",
                "steps": [
                    {"action": "delete_file", "parameters": {"path": "test.txt"}}
                ],
                "requires_confirmation": True,
            }
        ),
    },
]


def build_user_prompt(user_input: str) -> str:
    """Build a strict prompt payload with few-shot examples and user request."""
    example_lines: list[str] = []
    for example in FEW_SHOT_EXAMPLES:
        example_lines.append(f"Input: {example['input']}")
        example_lines.append(f"Output: {example['output']}")

    examples_block = "\n".join(example_lines)
    return (
        "Convert the following request into JSON plan.\n"
        "Follow the schema strictly and output JSON only.\n\n"
        f"Examples:\n{examples_block}\n\n"
        f"Input: {user_input}\n"
        "Output:"
    )
