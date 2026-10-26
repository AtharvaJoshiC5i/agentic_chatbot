"""One-off probe: does Gemini OpenAI-compat return thought_signature on tool calls?"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

key = os.environ.get("GEMINI_API_KEY", "").strip()
model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()
if not key:
    raise SystemExit("GEMINI_API_KEY not set")

client = OpenAI(
    api_key=key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_return_details",
            "description": "Get return",
            "parameters": {
                "type": "object",
                "properties": {"return_id": {"type": "string"}},
                "required": ["return_id"],
            },
        },
    }
]

r1 = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Call get_return_details for R105"}],
    tools=tools,
)
msg = r1.choices[0].message.model_dump()
print("TURN1", json.dumps(msg, indent=2)[:2000])
tc = msg.get("tool_calls") or []
if not tc:
    raise SystemExit("no tool calls")

r2 = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "user", "content": "Call get_return_details for R105"},
        {"role": "assistant", "content": msg.get("content") or "", "tool_calls": tc},
        {"role": "tool", "tool_call_id": tc[0]["id"], "content": '{"return_id":"R105"}'},
    ],
    tools=tools,
)
print("TURN2 OK", (r2.choices[0].message.content or "")[:200])
