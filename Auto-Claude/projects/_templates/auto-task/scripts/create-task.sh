#!/bin/bash
# {SKILL_PREFIX}-auto-task: Auto-Claude Task 생성 및 실행 스크립트
#
# Usage:
#   ./create-task.sh "task description" [project-path] [--no-build]

set -e

# Configuration — 프로젝트에 맞게 변경
AUTO_CLAUDE_BACKEND="{CLONE_DIR}/apps/backend"
PYTHON="$AUTO_CLAUDE_BACKEND/.venv/Scripts/python.exe"
SPEC_RUNNER="$AUTO_CLAUDE_BACKEND/runners/spec_runner.py"
RUN_PY="$AUTO_CLAUDE_BACKEND/run.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Arguments
TASK_DESC="$1"
PROJECT_PATH="${2:-{PROJECT_DIR}}"
NO_BUILD="$3"

# Validate
if [ -z "$TASK_DESC" ]; then
    echo -e "${RED}Error: Task description required${NC}"
    echo "Usage: $0 \"task description\" [project-path] [--no-build]"
    exit 1
fi

echo -e "${BLUE}======================================${NC}"
echo -e "${YELLOW}{PROJECT_NAME} Auto-Task${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${GREEN}Task:${NC} $TASK_DESC"
echo -e "${GREEN}Project:${NC} $PROJECT_PATH"
echo ""

# Step 1: Create spec
echo -e "${YELLOW}[1/3] Creating spec...${NC}"
PYTHONUTF8=1 USE_CLAUDE_MD=true $PYTHON "$SPEC_RUNNER" \
    --project-dir "$PROJECT_PATH" \
    --task "$TASK_DESC" \
    --complexity simple \
    --no-build

# Get spec number
SPEC_NUM=$(ls -1 "$PROJECT_PATH/.auto-claude/specs/" | grep -E "^[0-9]+-pending$" | sort -n | tail -1)

if [ -z "$SPEC_NUM" ]; then
    echo -e "${RED}Error: Could not find created spec${NC}"
    exit 1
fi

echo -e "${GREEN}Spec created: $SPEC_NUM${NC}"

# Step 2: Run build (if not --no-build)
if [ "$NO_BUILD" != "--no-build" ]; then
    echo ""
    echo -e "${YELLOW}[2/3] Running build...${NC}"
    PYTHONUTF8=1 USE_CLAUDE_MD=true $PYTHON "$RUN_PY" \
        --project-dir "$PROJECT_PATH" \
        --spec "$SPEC_NUM" \
        --force \
        --auto-continue

    echo -e "${GREEN}Build complete${NC}"
else
    echo ""
    echo -e "${YELLOW}[2/3] Skipped build (--no-build)${NC}"
    echo -e "${YELLOW}[3/3] Skipped status sync${NC}"
fi

echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}Done!${NC}"
echo -e "${BLUE}======================================${NC}"
