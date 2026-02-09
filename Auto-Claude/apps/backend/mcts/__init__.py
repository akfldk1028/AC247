"""
MCTS Multi-Path Search Module
===============================

Monte Carlo Tree Search for exploring multiple solution approaches
in parallel. The orchestrator creates child specs that the daemon
executes, then scores and compares results.

Public API:
    from mcts import run_mcts_search, MCTSResult

    result = await run_mcts_search(
        project_dir=project_dir,
        spec_dir=spec_dir,
        model="sonnet",
        max_iterations=10,
    )

Architecture:
    Pure Python (algorithm):       LLM agents (1 role each):
    ├── tree.py (data structures)  ├── idea_generator (ideas)
    ├── budget.py (budget)         ├── improver (refinements)
    ├── scorer.py (scoring)        ├── debugger (failure analysis)
    └── orchestrator.py (loop)     └── lesson_extractor (lessons)
"""

from .orchestrator import MCTSResult, run_mcts_search
from .tree import MCTSNode, MCTSTree
from .budget import BudgetTracker
from .scorer import BranchScore, score_branch

__all__ = [
    "run_mcts_search",
    "MCTSResult",
    "MCTSTree",
    "MCTSNode",
    "BudgetTracker",
    "BranchScore",
    "score_branch",
]


async def query_llm(client, prompt: str) -> str:
    """Send a single-turn query to a ClaudeSDKClient and collect the response.

    This is the correct pattern for the Claude Agent SDK:
        async with client:
            await client.query(prompt)
            async for msg in client.receive_response(): ...

    Args:
        client: A ClaudeSDKClient (already inside ``async with`` or not).
        prompt: The user prompt to send.

    Returns:
        Concatenated text from all AssistantMessage TextBlocks.
    """
    await client.query(prompt)

    response_text = ""
    async for msg in client.receive_response():
        msg_type = type(msg).__name__
        if msg_type == "AssistantMessage" and hasattr(msg, "content"):
            for block in msg.content:
                if hasattr(block, "text"):
                    response_text += block.text

    return response_text.strip()
