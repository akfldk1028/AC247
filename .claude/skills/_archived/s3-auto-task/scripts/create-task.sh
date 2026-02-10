#!/bin/bash
# s3-auto-task: Auto-Claude Task 생성 및 실행 스크립트
#
# Usage:
#   ./create-task.sh "task description" [project-path] [--no-build]
#
# Examples:
#   ./create-task.sh "Add login feature"
#   ./create-task.sh "Fix bug" /path/to/project
#   ./create-task.sh "Add feature" /path/to/project --no-build

set -e

# Configuration
AUTO_CLAUDE_BACKEND="C:/DK/S3/clone/Auto-Claude/apps/backend"
PYTHON="$AUTO_CLAUDE_BACKEND/.venv/Scripts/python.exe"
SPEC_RUNNER="$AUTO_CLAUDE_BACKEND/runners/spec_runner.py"
RUN_PY="$AUTO_CLAUDE_BACKEND/run.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Arguments
TASK_DESC="$1"
PROJECT_PATH="${2:-$(pwd)}"
NO_BUILD="$3"

# Validate
if [ -z "$TASK_DESC" ]; then
    echo -e "${RED}Error: Task description required${NC}"
    echo "Usage: $0 \"task description\" [project-path] [--no-build]"
    exit 1
fi

echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${YELLOW}🚀 S3 Auto-Task${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Task:${NC} $TASK_DESC"
echo -e "${GREEN}Project:${NC} $PROJECT_PATH"
echo ""

# Step 1: Create spec
echo -e "${YELLOW}[1/3] Creating spec...${NC}"
$PYTHON "$SPEC_RUNNER" \
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

echo -e "${GREEN}✓ Spec created: $SPEC_NUM${NC}"

# Step 2: Run build (if not --no-build)
if [ "$NO_BUILD" != "--no-build" ]; then
    echo ""
    echo -e "${YELLOW}[2/3] Running build...${NC}"
    $PYTHON "$RUN_PY" \
        --project-dir "$PROJECT_PATH" \
        --spec "$SPEC_NUM" \
        --force \
        --auto-continue

    echo -e "${GREEN}✓ Build complete${NC}"

    # Step 3: Add status for UI
    echo ""
    echo -e "${YELLOW}[3/3] Syncing status for UI...${NC}"

    # Worktree spec
    WT_SPEC="$PROJECT_PATH/.auto-claude/worktrees/tasks/$SPEC_NUM/.auto-claude/specs/$SPEC_NUM/implementation_plan.json"
    if [ -f "$WT_SPEC" ]; then
        sed -i 's/}$/,\n  "status": "human_review",\n  "xstateState": "human_review",\n  "executionPhase": "complete"\n}/' "$WT_SPEC" 2>/dev/null || true
        echo -e "${GREEN}✓ Worktree status synced${NC}"
    fi

    # Main spec
    MAIN_SPEC="$PROJECT_PATH/.auto-claude/specs/$SPEC_NUM/implementation_plan.json"
    if [ -f "$MAIN_SPEC" ]; then
        sed -i 's/}$/,\n  "status": "human_review",\n  "xstateState": "human_review",\n  "executionPhase": "complete"\n}/' "$MAIN_SPEC" 2>/dev/null || true
        echo -e "${GREEN}✓ Main status synced${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}[2/3] Skipped build (--no-build)${NC}"
    echo -e "${YELLOW}[3/3] Skipped status sync${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Done!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""
echo "Next steps:"
echo "  1. Refresh UI (F5)"
echo "  2. Check Human Review column"
echo "  3. Click Merge to apply changes"
