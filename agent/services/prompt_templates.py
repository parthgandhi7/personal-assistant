"""Prompt templates for strict natural-language command planning."""

from __future__ import annotations

import json

ALLOWED_ACTIONS: dict[str, dict[str, str]] = {
    "open_application": {
        "application": "string (required): application name to open, e.g. 'chrome' or 'vscode'",
    },
    "search_file": {
        "query": "string (required): filename or file pattern to search for",
        "directory": "string (optional): absolute or user-home-relative directory path",
    },
    "open_file": {
        "path": "string (required): absolute or user-home-relative file path",
    },
    "open_browser": {
        "browser": "string (optional): browser name, default 'chrome' if unspecified",
    },
    "search_web": {
        "query": "string (required): web search query",
    },
    "increase_volume": {
        "amount": "integer (optional): volume increment percent, default 10",
    },
    "decrease_volume": {
        "amount": "integer (optional): volume decrement percent, default 10",
    },
}

SYSTEM_PROMPT = """You are a deterministic execution planner for a local AI agent.

Your only job: convert a user request into a STRICT JSON execution plan.
Do not provide explanations. Do not output markdown. Do not output code fences.
Output must be valid JSON only.

Hard constraints:
1) Return EXACTLY one JSON object with keys:
   - intent: string
   - steps: non-empty array of step objects
   - requires_confirmation: boolean
2) Every step object must have keys:
   - action: one of the allowed actions
   - parameters: object
3) Never include actions outside the allowed list.
4) Never include shell commands, scripts, or arbitrary execution instructions.
5) Never pass through raw user text as a command.
6) If user asks for unsafe/unsupported action, return a safe plan that asks confirmation and uses the closest allowed action(s) only.

Allowed actions and parameter contracts:
- open_application: {application: string}
- search_file: {query: string, directory?: string}
- open_file: {path: string}
- open_browser: {browser?: string}
- search_web: {query: string}
- increase_volume: {amount?: integer}
- decrease_volume: {amount?: integer}

Planning rules:
- Keep steps minimal and executable.
- Use requires_confirmation=true for destructive, ambiguous, or potentially risky intents.
- If user mentions browser + search intent, split into open_browser then search_web.
- Infer obvious defaults when needed (e.g., browser='chrome').
"""

FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    {
        "input": "open chrome and search youtube",
        "output": json.dumps(
            {
                "intent": "Open browser and search YouTube",
                "steps": [
                    {"action": "open_browser", "parameters": {"browser": "chrome"}},
                    {"action": "search_web", "parameters": {"query": "YouTube"}},
                ],
                "requires_confirmation": False,
            }
        ),
    },
    {
        "input": "find report.pdf in my documents",
        "output": json.dumps(
            {
                "intent": "Search for report.pdf in Documents",
                "steps": [
                    {
                        "action": "search_file",
                        "parameters": {"query": "report.pdf", "directory": "~/Documents"},
                    }
                ],
                "requires_confirmation": False,
            }
        ),
    },
    {
        "input": "turn the volume down by 20 percent",
        "output": json.dumps(
            {
                "intent": "Decrease system volume",
                "steps": [
                    {
                        "action": "decrease_volume",
                        "parameters": {"amount": 20},
                    }
                ],
                "requires_confirmation": False,
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
