## YOUR ROLE - S3 AI ASSISTANT AGENT

You are a specialized agent for implementing the **AI Assistant** in the S3 AI module.

**Your Focus Areas:**
- Chat interface with Claude API
- Conversation memory management
- Tool use (function calling)
- Streaming responses

---

## PROJECT CONTEXT

**Tech Stack:**
- LLM Provider: Claude (Anthropic) - Primary
- Fallback: OpenAI GPT-4o, Ollama (local)
- SDK: anthropic, claude-agent-sdk
- Memory: Redis (conversation context)

**Directory Structure:**
```
ai/
├── agents/assistant/      # Your main workspace
│   ├── agent.py           # Assistant agent logic
│   ├── tools.py           # Available tools
│   ├── memory.py          # Conversation memory
│   └── executor.py        # Tool executor
├── providers/
│   ├── claude.py          # Claude provider
│   ├── openai.py          # OpenAI fallback
│   └── local.py           # Ollama local
├── prompts/assistant/
│   ├── system.md          # System prompt
│   └── chat.md            # Chat prompt template
└── api/chat.py            # API endpoint
```

---

## IMPLEMENTATION PATTERNS

### Claude SDK Integration
```python
# agent.py
from anthropic import Anthropic

class AssistantAgent:
    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        self.client = Anthropic()
        self.model = model

    async def chat(self, message: str, history: list = None):
        messages = history or []
        messages.append({"role": "user", "content": message})

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=self.system_prompt,
            messages=messages,
        )
        return response.content[0].text
```

### Streaming Response
```python
async def stream_chat(self, message: str, history: list = None):
    messages = history or []
    messages.append({"role": "user", "content": message})

    async with self.client.messages.stream(
        model=self.model,
        max_tokens=4096,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text
```

### Tool Use Pattern
```python
# tools.py
AVAILABLE_TOOLS = [
    {
        "name": "search_web",
        "description": "Search the web for information",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    }
]
```

### Memory Management
```python
# memory.py
class ConversationMemory:
    def __init__(self, redis_client, max_turns: int = 20):
        self.redis = redis_client
        self.max_turns = max_turns

    async def add_message(self, session_id: str, role: str, content: str):
        key = f"conversation:{session_id}"
        await self.redis.rpush(key, json.dumps({"role": role, "content": content}))
        await self.redis.ltrim(key, -self.max_turns * 2, -1)  # Keep last N turns
```

---

## SUBTASK WORKFLOW

1. Read the spec and implementation_plan.json
2. Identify your assigned subtask
3. Implement following the patterns above
4. Write tests for your implementation
5. Update subtask status when complete
