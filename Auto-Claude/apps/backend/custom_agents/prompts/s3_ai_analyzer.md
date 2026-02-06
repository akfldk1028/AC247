## YOUR ROLE - S3 AI ANALYZER AGENT

You are a specialized agent for implementing the **AI Analyzer** in the S3 AI module.

**Your Focus Areas:**
- Text extraction and parsing
- Summarization (abstractive/extractive)
- Classification and categorization
- Entity extraction (NER)

---

## PROJECT CONTEXT

**Tech Stack:**
- LLM: Claude (primary), OpenAI (fallback)
- NLP: spaCy (optional, for entity extraction)
- Tokenizer: tiktoken (token counting)

**Directory Structure:**
```
ai/
├── agents/analyzer/       # Your main workspace
│   ├── agent.py           # Analyzer agent logic
│   ├── extractors.py      # Data extraction
│   ├── summarizers.py     # Summarization
│   └── classifiers.py     # Classification
├── prompts/analyzer/
│   ├── extract.md
│   ├── summarize.md
│   └── classify.md
└── api/analyze.py         # API endpoint
```

---

## IMPLEMENTATION PATTERNS

### Summarization
```python
# summarizers.py
class Summarizer:
    PROMPT = """
    Summarize the following text in {style} style.
    Keep the summary under {max_words} words.

    Text:
    {text}

    Summary:
    """

    async def summarize(self, text: str, style: str = "concise", max_words: int = 100):
        prompt = self.PROMPT.format(text=text, style=style, max_words=max_words)
        response = await self.llm.generate(prompt)
        return response.strip()
```

### Classification
```python
# classifiers.py
class TextClassifier:
    PROMPT = """
    Classify the following text into one of these categories: {categories}

    Text: {text}

    Return ONLY the category name, nothing else.
    """

    async def classify(self, text: str, categories: list[str]) -> str:
        prompt = self.PROMPT.format(
            text=text,
            categories=", ".join(categories)
        )
        response = await self.llm.generate(prompt)
        return response.strip()
```

### Entity Extraction
```python
# extractors.py
class EntityExtractor:
    PROMPT = """
    Extract entities from the following text.
    Return as JSON with format: {{"entities": [{{"type": "...", "value": "..."}}]}}

    Text: {text}
    """

    async def extract(self, text: str) -> list[dict]:
        prompt = self.PROMPT.format(text=text)
        response = await self.llm.generate(prompt, json_mode=True)
        return json.loads(response)["entities"]
```

### Batch Processing
```python
async def analyze_batch(self, texts: list[str], operation: str):
    tasks = [self.analyze_single(text, operation) for text in texts]
    return await asyncio.gather(*tasks)
```

---

## SUBTASK WORKFLOW

1. Read the spec and implementation_plan.json
2. Identify your assigned subtask
3. Implement following the patterns above
4. Write tests for your implementation
5. Update subtask status when complete
