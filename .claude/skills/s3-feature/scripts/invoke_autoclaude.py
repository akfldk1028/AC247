"""
Auto-Claude Agent Invoker
=========================

Claude Skills에서 Auto-Claude의 커스텀 에이전트를 호출하는 스크립트.

Usage:
    python invoke_autoclaude.py --agent s3_backend_auth --task "JWT 인증 구현"
    python invoke_autoclaude.py --list  # 사용 가능한 에이전트 목록
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Auto-Claude 경로
AUTO_CLAUDE_BACKEND = Path("C:/DK/S3/S3/Auto-Claude/apps/backend")
PYTHON_PATH = AUTO_CLAUDE_BACKEND / ".venv/Scripts/python.exe"

# 사용 가능한 S3 커스텀 에이전트
S3_AGENTS = {
    "s3_backend_auth": "Backend 인증 (JWT, OAuth, Session)",
    "s3_backend_data": "Backend 데이터 (CRUD, Query, Cache)",
    "s3_backend_notification": "Backend 알림 (Push, Email, SMS)",
    "s3_ai_assistant": "AI 어시스턴트 (LLM 기반)",
    "s3_ai_analyzer": "AI 분석기 (데이터 분석, 요약)",
    "s3_ai_recommender": "AI 추천 시스템",
    "s3_frontend_auth": "Frontend 인증 UI (Flutter)",
    "s3_frontend_data": "Frontend 데이터 동기화 (Flutter)",
}


def list_agents():
    """사용 가능한 에이전트 목록 출력"""
    print("\n=== S3 Custom Agents ===\n")
    for agent, desc in S3_AGENTS.items():
        print(f"  {agent:25} - {desc}")
    print()


def invoke_agent(agent_type: str, task: str) -> tuple[str, str]:
    """
    Auto-Claude 에이전트 호출

    Args:
        agent_type: 에이전트 타입 (예: s3_backend_auth)
        task: 실행할 작업 설명

    Returns:
        (stdout, stderr) 튜플
    """
    if agent_type not in S3_AGENTS:
        print(f"Error: Unknown agent '{agent_type}'")
        print("Use --list to see available agents")
        sys.exit(1)

    # run.py가 에이전트 타입을 지원하는지 확인
    # 현재 Auto-Claude 구조에서는 spec을 통해 에이전트가 실행됨
    # 여기서는 직접적인 에이전트 호출 대신 가이드 출력

    print(f"\n=== Invoking Agent: {agent_type} ===")
    print(f"Task: {task}\n")

    # Auto-Claude spec 생성 가이드
    guide = f"""
To use this agent with Auto-Claude:

1. Create a spec:
   cd {AUTO_CLAUDE_BACKEND}
   {PYTHON_PATH} spec_runner.py --task "{task}"

2. Or use the custom agent prompt directly:
   The agent prompt is at:
   {AUTO_CLAUDE_BACKEND / 'custom_agents/prompts' / f'{agent_type}.md'}

3. Agent capabilities:
   - {S3_AGENTS[agent_type]}
"""
    print(guide)
    return "", ""


def main():
    parser = argparse.ArgumentParser(
        description="Invoke Auto-Claude agents from Claude Skills"
    )
    parser.add_argument(
        "--agent", "-a",
        help="Agent type to invoke (e.g., s3_backend_auth)"
    )
    parser.add_argument(
        "--task", "-t",
        help="Task description"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available agents"
    )

    args = parser.parse_args()

    if args.list:
        list_agents()
        return

    if not args.agent or not args.task:
        parser.print_help()
        print("\nExamples:")
        print("  python invoke_autoclaude.py --agent s3_backend_auth --task 'JWT 인증 구현'")
        print("  python invoke_autoclaude.py --list")
        return

    invoke_agent(args.agent, args.task)


if __name__ == "__main__":
    main()
