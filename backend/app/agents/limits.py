"""Token/rate-conscious limits for agent ↔ LLM traffic."""

# Conversation sent to the model on each turn (count + token budget; see history.py)
MAX_HISTORY_TURNS = 8
MAX_TURN_CHARS = 2_000
# Tool outputs echoed back into the agent loop
MAX_TOOL_JSON_CHARS = 2_500

# RAG document tool result cap
MAX_DOC_SEARCH_RESULTS = 3
