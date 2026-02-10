"""
Auto-Claude Agent Invoker
=========================

Claude Skills에서 Auto-Claude의 커스텀 에이전트를 호출하는 스크립트.

Usage:
    python invoke_autoclaude.py --agent {SKILL_PREFIX}_agent_name --task "기능 구현"
    python invoke_autoclaude.py --list  # 사용 가능한 에이전트 목록
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Auto-Claude 경로 — 프로젝트에 맞게 변경
AUTO_CLAUDE_BACKEND = Path("{CLONE_DIR}/apps/backend")
PYTHON_PATH = AUTO_CLAUDE_BACKEND / ".venv/Scripts/python.exe"

# 사용 가능한 커스텀 에이전트 — 프로젝트에 맞게 변경
PROJECT_AGENTS = {
    # "{SKILL_PREFIX}_agent_1": "에이전트 1 설명",
    # "{SKILL_PREFIX}_agent_2": "에이전트 2 설명",
}


def list_agents():
    """사용 가능한 에이전트 목록 출력"""
    print("\n=== {PROJECT_NAME} Custom Agents ===\n")
    for agent, desc in PROJECT_AGENTS.items():
        print(f"  {agent:25} - {desc}")
    print()


def invoke_agent(agent_type: str, task: str) -> tuple[str, str]:
    """Auto-Claude 에이전트 호출"""
    if agent_type not in PROJECT_AGENTS:
        print(f"Error: Unknown agent '{agent_type}'")
        print("Use --list to see available agents")
        sys.exit(1)

    print(f"\n=== Invoking Agent: {agent_type} ===")
    print(f"Task: {task}\n")

    guide = f"""
To use this agent with Auto-Claude:

1. Create a spec:
   cd {AUTO_CLAUDE_BACKEND}
   {PYTHON_PATH} spec_runner.py --task "{task}"

2. Agent capabilities:
   - {PROJECT_AGENTS[agent_type]}
"""
    print(guide)
    return "", ""


def main():
    parser = argparse.ArgumentParser(
        description="Invoke Auto-Claude agents from Claude Skills"
    )
    parser.add_argument("--agent", "-a", help="Agent type to invoke")
    parser.add_argument("--task", "-t", help="Task description")
    parser.add_argument("--list", "-l", action="store_true", help="List available agents")

    args = parser.parse_args()

    if args.list:
        list_agents()
        return

    if not args.agent or not args.task:
        parser.print_help()
        return

    invoke_agent(args.agent, args.task)


if __name__ == "__main__":
    main()
