"""
Tool Models and Constants
==========================

Defines tool name constants and configuration for auto-claude MCP tools.

This module delegates to core.agent_registry (unified AgentRegistry) for
agent configuration. The AGENT_CONFIGS dict and public API functions remain
unchanged for backward compatibility.

- Base tools: Core file operations (Read, Write, Edit, etc.)
- Web tools: Documentation and research (WebFetch, WebSearch)
- MCP tools: External integrations (Context7, Linear, Graphiti, etc.)
- Auto-Claude tools: Custom build management tools
- Custom agents: User-defined agents from custom_agents/config.json
"""

import logging
import os
from pathlib import Path

from core.agent_registry import (
    BASE_READ_TOOLS,
    BASE_WRITE_TOOLS,
    TOOL_CREATE_BATCH_CHILD_SPECS,
    TOOL_CREATE_CHILD_SPEC,
    TOOL_GET_BUILD_PROGRESS,
    TOOL_GET_SESSION_CONTEXT,
    TOOL_RECORD_DISCOVERY,
    TOOL_RECORD_GOTCHA,
    TOOL_UPDATE_QA_STATUS,
    TOOL_UPDATE_SUBTASK_STATUS,
    WEB_TOOLS,
)

logger = logging.getLogger(__name__)

# =============================================================================
# External MCP Tools
# =============================================================================

# Context7 MCP tools for documentation lookup (always enabled)
CONTEXT7_TOOLS = [
    "mcp__context7__resolve-library-id",
    "mcp__context7__get-library-docs",
]

# Linear MCP tools for project management (when LINEAR_API_KEY is set)
LINEAR_TOOLS = [
    "mcp__linear-server__list_teams",
    "mcp__linear-server__get_team",
    "mcp__linear-server__list_projects",
    "mcp__linear-server__get_project",
    "mcp__linear-server__create_project",
    "mcp__linear-server__update_project",
    "mcp__linear-server__list_issues",
    "mcp__linear-server__get_issue",
    "mcp__linear-server__create_issue",
    "mcp__linear-server__update_issue",
    "mcp__linear-server__list_comments",
    "mcp__linear-server__create_comment",
    "mcp__linear-server__list_issue_statuses",
    "mcp__linear-server__list_issue_labels",
    "mcp__linear-server__list_users",
    "mcp__linear-server__get_user",
]

# Graphiti MCP tools for knowledge graph memory (when GRAPHITI_MCP_URL is set)
# See: https://github.com/getzep/graphiti
GRAPHITI_MCP_TOOLS = [
    "mcp__graphiti-memory__search_nodes",  # Search entity summaries
    "mcp__graphiti-memory__search_facts",  # Search relationships between entities
    "mcp__graphiti-memory__add_episode",  # Add data to knowledge graph
    "mcp__graphiti-memory__get_episodes",  # Retrieve recent episodes
    "mcp__graphiti-memory__get_entity_edge",  # Get specific entity/relationship
]

# =============================================================================
# Browser Automation MCP Tools (QA agents only)
# =============================================================================

# Playwright MCP tools for web browser automation (@playwright/mcp)
# Used for web frontend validation (non-Electron web apps)
# Uses accessibility snapshots instead of CSS selectors — works with Flutter CanvasKit too.
# NOTE: Screenshots must be compressed to stay under Claude SDK's 1MB JSON message buffer limit.
PLAYWRIGHT_TOOLS = [
    "mcp__playwright__browser_navigate",
    "mcp__playwright__browser_navigate_back",
    "mcp__playwright__browser_navigate_forward",
    "mcp__playwright__browser_snapshot",
    "mcp__playwright__browser_take_screenshot",
    "mcp__playwright__browser_click",
    "mcp__playwright__browser_type",
    "mcp__playwright__browser_hover",
    "mcp__playwright__browser_select_option",
    "mcp__playwright__browser_press_key",
    "mcp__playwright__browser_console_messages",
    "mcp__playwright__browser_tab_list",
    "mcp__playwright__browser_tab_new",
    "mcp__playwright__browser_tab_select",
    "mcp__playwright__browser_close",
    "mcp__playwright__browser_wait_for",
    "mcp__playwright__browser_resize",
]

# Electron MCP tools for desktop app automation (when ELECTRON_MCP_ENABLED is set)
# Uses electron-mcp-server to connect to Electron apps via Chrome DevTools Protocol.
# Electron app must be started with --remote-debugging-port=9222 (or ELECTRON_DEBUG_PORT).
# These tools are only available to QA agents (qa_reviewer, qa_fixer), not Coder/Planner.
# NOTE: Screenshots must be compressed to stay under Claude SDK's 1MB JSON message buffer limit.
ELECTRON_TOOLS = [
    "mcp__electron__get_electron_window_info",  # Get info about running Electron windows
    "mcp__electron__take_screenshot",  # Capture screenshot of Electron window
    "mcp__electron__send_command_to_electron",  # Send commands (click, fill, evaluate JS)
    "mcp__electron__read_electron_logs",  # Read console logs from Electron app
]

# Marionette MCP tools for Flutter runtime interaction (leancodepl/marionette_mcp)
# Connects to running Flutter apps via VM Service protocol for widget-level interaction.
# Requires: dart pub global activate marionette_mcp
# Requires: marionette_flutter package added to the Flutter app + MarionetteBinding in main.dart
MARIONETTE_TOOLS = [
    "mcp__marionette__connect",                  # Connect to Flutter app via VM service URI
    "mcp__marionette__disconnect",               # Disconnect from the app
    "mcp__marionette__get_interactive_elements",  # List all interactive widgets on screen
    "mcp__marionette__tap",                       # Tap a widget by key or text
    "mcp__marionette__enter_text",                # Enter text into a text field
    "mcp__marionette__scroll_to",                 # Scroll until element is visible
    "mcp__marionette__get_logs",                  # Retrieve app logs
    "mcp__marionette__take_screenshots",          # Capture screenshots (base64)
    "mcp__marionette__hot_reload",                # Hot reload the app
]

# =============================================================================
# Configuration
# =============================================================================


def is_electron_mcp_enabled() -> bool:
    """
    Check if Electron MCP server integration is enabled.

    Requires ELECTRON_MCP_ENABLED to be set to 'true'.
    When enabled, QA agents can use Electron MCP tools to connect to Electron apps
    via Chrome DevTools Protocol on the configured debug port.
    """
    return os.environ.get("ELECTRON_MCP_ENABLED", "").lower() == "true"


# =============================================================================
# Agent Configuration Registry (backed by AgentRegistry)
# =============================================================================
# AGENT_CONFIGS is now a shim that reads from core.agent_registry.
# All agent definitions live in core/agent_registry.py (single source of truth).
# Public API functions below remain unchanged for backward compatibility.


def _build_agent_configs() -> dict:
    """Build AGENT_CONFIGS dict from the unified AgentRegistry.

    Returns a plain dict that behaves identically to the old AGENT_CONFIGS.
    """
    from core.agent_registry import AgentRegistry

    registry = AgentRegistry.instance()
    configs = {}
    for agent_id, defn in registry.all_agents().items():
        configs[agent_id] = defn.to_agent_config_dict()
    return configs


# Build once at module load — identical to old behavior
AGENT_CONFIGS = _build_agent_configs()

# Re-export custom agents dir for backward compat
CUSTOM_AGENTS_DIR = Path(__file__).parent.parent.parent / "custom_agents"
CUSTOM_AGENTS_CONFIG = CUSTOM_AGENTS_DIR / "config.json"


def get_custom_agent_prompt(agent_type: str) -> str | None:
    """
    Load prompt content for a custom agent.

    Args:
        agent_type: The custom agent type identifier

    Returns:
        Prompt content as string, or None if not a custom agent
    """
    from core.agent_registry import AgentRegistry

    reg = AgentRegistry.instance()
    defn = reg.get(agent_type)
    if defn is None or not defn.is_custom:
        return None

    prompt_path = defn.custom_prompt_file
    if not prompt_path:
        return None

    try:
        return Path(prompt_path).read_text(encoding="utf-8")
    except OSError as e:
        logger.error(f"Failed to load custom agent prompt: {e}")
        return None


def list_custom_agents() -> list[dict]:
    """
    List all registered custom agents with their metadata.

    Returns:
        List of dicts with agent_type, description, prompt_file
    """
    from core.agent_registry import AgentRegistry

    reg = AgentRegistry.instance()
    result = []
    for agent_id, defn in reg.all_agents().items():
        if defn.is_custom:
            result.append({
                "agent_type": agent_id,
                "description": defn.description,
                "prompt_file": defn.custom_prompt_file or "",
            })
    return result


def get_custom_agent_executor_configs() -> dict[str, dict]:
    """
    Return custom agent execution configs for executor.py AGENT_REGISTRY.

    Called by executor.py to auto-register custom agents into AGENT_REGISTRY
    so they get the right execution config (use_claude_cli, script, prompt_template).

    Returns:
        Dict mapping agent_type → executor config props
    """
    from core.agent_registry import AgentRegistry

    reg = AgentRegistry.instance()
    result = {}
    for agent_id, defn in reg.all_agents().items():
        if not defn.is_custom:
            continue
        result[agent_id] = defn.to_executor_config_dict()
    return result


# =============================================================================
# Agent Config Helper Functions
# =============================================================================


def get_agent_config(agent_type: str) -> dict:
    """
    Get full configuration for an agent type.

    Args:
        agent_type: The agent type identifier (e.g., 'coder', 'planner', 'qa_reviewer')

    Returns:
        Configuration dict containing tools, mcp_servers, auto_claude_tools, thinking_default

    Raises:
        ValueError: If agent_type is not found in AGENT_CONFIGS (strict mode)
    """
    if agent_type not in AGENT_CONFIGS:
        raise ValueError(
            f"Unknown agent type: '{agent_type}'. "
            f"Valid types: {sorted(AGENT_CONFIGS.keys())}"
        )
    return AGENT_CONFIGS[agent_type]


def _map_mcp_server_name(
    name: str, custom_server_ids: list[str] | None = None
) -> str | None:
    """
    Map user-friendly MCP server names to internal identifiers.
    Also accepts custom server IDs directly.

    Args:
        name: User-provided MCP server name
        custom_server_ids: List of custom server IDs to accept as-is

    Returns:
        Internal server identifier or None if not recognized
    """
    if not name:
        return None
    mappings = {
        "context7": "context7",
        "graphiti-memory": "graphiti",
        "graphiti": "graphiti",
        "linear": "linear",
        "electron": "electron",
        "puppeteer": "playwright",  # backwards compat alias
        "playwright": "playwright",
        "marionette": "marionette",
        "auto-claude": "auto-claude",
    }
    # Check if it's a known mapping
    mapped = mappings.get(name.lower().strip())
    if mapped:
        return mapped
    # Check if it's a custom server ID (accept as-is)
    if custom_server_ids and name in custom_server_ids:
        return name
    return None


def get_required_mcp_servers(
    agent_type: str,
    project_capabilities: dict | None = None,
    linear_enabled: bool = False,
    mcp_config: dict | None = None,
) -> list[str]:
    """
    Get MCP servers required for this agent type.

    Handles dynamic server selection:
    - "browser" → electron (if is_electron) or playwright (if web/flutter/expo/tauri)
    - "linear" → only if in mcp_servers_optional AND linear_enabled is True
    - "graphiti" → only if GRAPHITI_MCP_URL is set
    - Respects per-project MCP config overrides from .auto-claude/.env
    - Applies per-agent ADD/REMOVE overrides from AGENT_MCP_<agent>_ADD/REMOVE

    Args:
        agent_type: The agent type identifier
        project_capabilities: Dict from detect_project_capabilities() or None
        linear_enabled: Whether Linear integration is enabled for this project
        mcp_config: Per-project MCP server toggles from .auto-claude/.env
                   Keys: CONTEXT7_ENABLED, LINEAR_MCP_ENABLED, ELECTRON_MCP_ENABLED,
                         BROWSER_MCP_DISABLED, AGENT_MCP_<agent>_ADD/REMOVE

    Returns:
        List of MCP server names to start
    """
    config = get_agent_config(agent_type)
    servers = list(config.get("mcp_servers", []))

    # Load per-project config (or use defaults)
    if mcp_config is None:
        mcp_config = {}

    # Filter context7 if explicitly disabled by project config
    if "context7" in servers:
        context7_enabled = mcp_config.get("CONTEXT7_ENABLED", "true")
        if str(context7_enabled).lower() == "false":
            servers = [s for s in servers if s != "context7"]

    # Handle optional servers (e.g., Linear if project setting enabled)
    optional = config.get("mcp_servers_optional", [])
    if "linear" in optional and linear_enabled:
        # Also check per-project LINEAR_MCP_ENABLED override
        linear_mcp_enabled = mcp_config.get("LINEAR_MCP_ENABLED", "true")
        if str(linear_mcp_enabled).lower() != "false":
            servers.append("linear")

    # Handle dynamic "browser" → electron/playwright based on project type and config
    if "browser" in servers:
        servers = [s for s in servers if s != "browser"]
        if project_capabilities:
            is_electron = project_capabilities.get("is_electron", False)
            is_web_frontend = project_capabilities.get("is_web_frontend", False)
            is_flutter = project_capabilities.get("is_flutter", False)
            is_expo = project_capabilities.get("is_expo", False)
            is_tauri = project_capabilities.get("is_tauri", False)

            needs_browser = is_web_frontend or is_flutter or is_expo or is_tauri

            # Check per-project overrides
            electron_enabled = mcp_config.get("ELECTRON_MCP_ENABLED", "false")

            # Electron: enabled by project config OR global env var
            if is_electron and (
                str(electron_enabled).lower() == "true" or is_electron_mcp_enabled()
            ):
                servers.append("electron")
            # Playwright: auto-enabled for web apps (opt-out via BROWSER_MCP_DISABLED=true)
            elif needs_browser and not is_electron:
                browser_disabled = mcp_config.get("BROWSER_MCP_DISABLED", "false")
                if str(browser_disabled).lower() != "true":
                    servers.append("playwright")

            # Marionette MCP: auto-enabled for Flutter projects (widget-level interaction)
            # Opt-out via MARIONETTE_MCP_DISABLED=true in .auto-claude/.env
            if is_flutter:
                marionette_disabled = mcp_config.get("MARIONETTE_MCP_DISABLED", "false")
                if str(marionette_disabled).lower() != "true":
                    servers.append("marionette")

    # Filter graphiti if not enabled
    if "graphiti" in servers:
        if not os.environ.get("GRAPHITI_MCP_URL"):
            servers = [s for s in servers if s != "graphiti"]

    # ========== Add custom MCP servers with agent-level targeting ==========
    # Custom servers can specify which agents they're available for:
    # - "agents": "*" → available to all agents
    # - "agents": ["planner", "coder"] → only for specific agents
    # - no "agents" field → available to all agents (default)
    custom_servers = mcp_config.get("CUSTOM_MCP_SERVERS", [])
    for custom in custom_servers:
        server_id = custom.get("id")
        if not server_id:
            continue

        # Check if this server is enabled for this agent type
        agents_filter = custom.get("agents", "*")
        if agents_filter == "*":
            # Available to all agents
            if server_id not in servers:
                servers.append(server_id)
        elif isinstance(agents_filter, list):
            # Only available to specific agents
            if agent_type in agents_filter and server_id not in servers:
                servers.append(server_id)

    # ========== Apply per-agent MCP overrides ==========
    # Format: AGENT_MCP_<agent_type>_ADD=server1,server2
    #         AGENT_MCP_<agent_type>_REMOVE=server1,server2
    add_key = f"AGENT_MCP_{agent_type}_ADD"
    remove_key = f"AGENT_MCP_{agent_type}_REMOVE"

    # Extract custom server IDs for mapping (allows custom servers to be recognized)
    custom_server_ids = [s.get("id") for s in custom_servers if s.get("id")]

    # Process additions
    if add_key in mcp_config:
        additions = [
            s.strip() for s in str(mcp_config[add_key]).split(",") if s.strip()
        ]
        for server in additions:
            mapped = _map_mcp_server_name(server, custom_server_ids)
            if mapped and mapped not in servers:
                servers.append(mapped)

    # Process removals (but never remove auto-claude)
    if remove_key in mcp_config:
        removals = [
            s.strip() for s in str(mcp_config[remove_key]).split(",") if s.strip()
        ]
        for server in removals:
            mapped = _map_mcp_server_name(server, custom_server_ids)
            if mapped and mapped != "auto-claude":  # auto-claude cannot be removed
                servers = [s for s in servers if s != mapped]

    return servers


def get_default_thinking_level(agent_type: str) -> str:
    """
    Get default thinking level string for agent type.

    This returns the thinking level name (e.g., 'medium', 'high'), not the token budget.
    To convert to tokens, use phase_config.get_thinking_budget(level).

    Args:
        agent_type: The agent type identifier

    Returns:
        Thinking level string (none, low, medium, high, ultrathink)
    """
    config = get_agent_config(agent_type)
    return config.get("thinking_default", "medium")
