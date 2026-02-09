import chokidar, { type FSWatcher } from 'chokidar';
import { readFileSync, existsSync } from 'fs';
import path from 'path';
import type { BrowserWindow } from 'electron';
import { fileWatcher } from './file-watcher';
import { safeSendToRenderer } from './ipc-handlers/utils';
import { IPC_CHANNELS } from '../shared/constants';

interface DaemonTaskInfo {
  spec_id: string;
  spec_dir: string;
  pid: number;
  status: string;
  started_at: string;
  last_update: string;
  is_running: boolean;
  task_type: string;
  current_subtask?: string;
  phase?: string;
  session?: number;
}

interface DaemonStatus {
  running: boolean;
  running_tasks: Record<string, DaemonTaskInfo>;
  queued_tasks: Array<{ spec_id: string; priority: number }>;
  stats: { running: number; queued: number; completed: number };
  timestamp: string;
  ws_port?: number;
}

interface ProjectWatcher {
  watcher: FSWatcher;
  statusFilePath: string;
  projectId: string;
  watchedTasks: Set<string>;
  previousRunningIds: Set<string>;
  previousCompleted: number;
  rendererReady: boolean;
  readyTimer: ReturnType<typeof setTimeout> | null;
  resendTimer: ReturnType<typeof setInterval> | null;
  /** All spec IDs ever seen (running + queued) — used to detect new specs */
  allKnownSpecIds: Set<string>;
  /** WebSocket connection to daemon (optional, for real-time updates) */
  ws: WebSocket | null;
  wsPort: number | null;
}

const daemonManagedTasks = new Map<string, string>();

/**
 * Check if a task is currently managed by the daemon process.
 * Used as fallback when agentManager.isRunning() returns false.
 */
export function isDaemonManaged(taskId: string): boolean {
  return daemonManagedTasks.has(taskId);
}

/**
 * Watches daemon_status.json and bridges daemon-managed tasks
 * to the existing fileWatcher/IPC pipeline so the UI auto-updates.
 *
 * Supports multiple projects simultaneously via per-project watcher Map.
 *
 * Key design decisions:
 * - Re-sends status for ALL running tasks on every processFile call (every 10s)
 *   because the initial event may arrive before the renderer is ready.
 *   The task store deduplicates identical status updates, so no wasted renders.
 * - Sends TASK_STATUS_CHANGE for transitions (start/stop) immediately.
 * - Uses fileWatcher for implementation_plan.json progress updates.
 */
export class DaemonStatusWatcher {
  private watchers: Map<string, ProjectWatcher> = new Map();
  private getMainWindow: (() => BrowserWindow | null) | null = null;

  start(
    statusFilePath: string,
    getMainWindow?: () => BrowserWindow | null,
    projectId?: string,
  ): void {
    const pid = projectId ?? statusFilePath;

    // Already watching this project — skip to avoid churn from polling
    if (this.watchers.has(pid)) return;

    if (!existsSync(statusFilePath)) return;

    // Skip if daemon is not running (prevents infinite re-create loop:
    // scanDaemonStatusFiles calls start() every 5s, stopProject() removes watcher,
    // next scan re-creates it, processFile sees running:false, stops again, ...)
    try {
      const content = readFileSync(statusFilePath, 'utf-8');
      const clean = content.charCodeAt(0) === 0xFEFF ? content.slice(1) : content;
      const status = JSON.parse(clean);
      if (!status.running) return;
    } catch {
      return;
    }

    this.getMainWindow = getMainWindow ?? this.getMainWindow;

    const pw: ProjectWatcher = {
      watcher: null!,
      statusFilePath,
      projectId: projectId ?? '',
      watchedTasks: new Set(),
      previousRunningIds: new Set(),
      previousCompleted: 0,
      rendererReady: false,
      readyTimer: null,
      resendTimer: null,
      allKnownSpecIds: new Set(),
      ws: null,
      wsPort: null,
    };

    // Delay initial processing to let renderer mount first
    pw.readyTimer = setTimeout(() => {
      pw.rendererReady = true;
      this.processFile(statusFilePath, pw);
    }, 5000);

    // Reduced stabilization threshold (100ms vs 500ms) since the daemon now
    // uses event-driven writes with atomic temp→rename. The file is complete
    // once detected. Poll interval lowered to match.
    pw.watcher = chokidar.watch(statusFilePath, {
      persistent: true,
      ignoreInitial: true,
      awaitWriteFinish: { stabilityThreshold: 100, pollInterval: 50 },
    });
    pw.watcher.on('change', () => this.processFile(statusFilePath, pw));
    pw.watcher.on('add', () => this.processFile(statusFilePath, pw));

    // Periodically re-send status for running tasks (every 3s).
    // This ensures the renderer stays in sync even after forceRefresh
    // clears the store and reloads from implementation_plan.json (which
    // has stale status). The task store deduplicates identical updates.
    pw.resendTimer = setInterval(() => {
      if (pw.rendererReady && pw.previousRunningIds.size > 0) {
        this.processFile(statusFilePath, pw);
      }
    }, 3000);

    this.watchers.set(pid, pw);
  }

  /**
   * Stop a specific project watcher, or all watchers if no projectId given.
   */
  stop(projectId?: string): void {
    if (projectId !== undefined) {
      this.stopProject(projectId);
    } else {
      for (const pid of [...this.watchers.keys()]) {
        this.stopProject(pid);
      }
    }
  }

  private stopProject(pid: string): void {
    const pw = this.watchers.get(pid);
    if (!pw) return;

    if (pw.readyTimer) {
      clearTimeout(pw.readyTimer);
      pw.readyTimer = null;
    }
    if (pw.resendTimer) {
      clearInterval(pw.resendTimer);
      pw.resendTimer = null;
    }
    pw.watcher?.close();

    // Clean up daemon-managed entries BEFORE clearing the sets
    for (const specId of pw.watchedTasks) {
      fileWatcher.unwatch(specId);
      daemonManagedTasks.delete(specId);
    }
    for (const specId of pw.previousRunningIds) {
      daemonManagedTasks.delete(specId);
    }

    // Close WebSocket connection
    if (pw.ws) {
      try { pw.ws.close(); } catch { /* ignore */ }
      pw.ws = null;
      pw.wsPort = null;
    }

    pw.watchedTasks.clear();
    pw.previousRunningIds.clear();
    pw.allKnownSpecIds.clear();
    pw.previousCompleted = 0;
    pw.rendererReady = false;

    this.watchers.delete(pid);
  }

  private processFile(statusPath: string, pw: ProjectWatcher): void {
    let status: DaemonStatus;
    try {
      const content = readFileSync(statusPath, 'utf-8');
      const clean = content.charCodeAt(0) === 0xFEFF ? content.slice(1) : content;
      status = JSON.parse(clean);
    } catch {
      return;
    }

    if (!status.running) {
      // Find the key for this ProjectWatcher and stop it
      for (const [pid, w] of this.watchers) {
        if (w === pw) {
          this.stopProject(pid);
          break;
        }
      }
      return;
    }

    // Auto-discover and connect to WebSocket server (if available)
    if (status.ws_port && status.ws_port !== pw.wsPort && !pw.ws) {
      this.connectWebSocket(pw, status.ws_port);
    }

    // Collect ALL spec IDs from both running and queued tasks
    const allCurrentIds = new Set<string>();
    const currentIds = new Set<string>();

    for (const [specId, info] of Object.entries(status.running_tasks || {})) {
      currentIds.add(specId);
      allCurrentIds.add(specId);
      daemonManagedTasks.set(specId, info.last_update || '');

      // Always re-send status for running tasks so renderer stays in sync.
      // The task store deduplicates identical updates (no wasted re-renders).
      if (pw.rendererReady) {
        this.sendStatusChange(specId, 'in_progress', pw.projectId);

        // Also send execution progress (phase badge) from daemon_status.json
        if (info.phase) {
          this.sendExecutionProgress(specId, info, pw.projectId);
        }
      }

      // Start file watcher for plan progress (leverages existing IPC pipeline)
      if (!pw.watchedTasks.has(specId) && !fileWatcher.isWatching(specId)) {
        if (existsSync(info.spec_dir)) {
          fileWatcher.watch(specId, info.spec_dir);
          pw.watchedTasks.add(specId);
        }
      }
    }

    // Send status for queued tasks so they appear in the Kanban board
    for (const queuedTask of status.queued_tasks || []) {
      allCurrentIds.add(queuedTask.spec_id);
      if (pw.rendererReady) {
        this.sendStatusChange(queuedTask.spec_id, 'queue', pw.projectId);
      }
    }

    // Detect newly discovered specs and trigger TASK_LIST refresh
    // This ensures child specs created by the daemon appear in the UI
    let hasNewSpecs = false;
    for (const specId of allCurrentIds) {
      if (!pw.allKnownSpecIds.has(specId)) {
        hasNewSpecs = true;
        pw.allKnownSpecIds.add(specId);
      }
    }
    if (hasNewSpecs && pw.rendererReady) {
      this.notifyNewSpecs(pw);
    }

    // Tasks that were running but are no longer → read actual status from plan
    for (const specId of pw.previousRunningIds) {
      if (!currentIds.has(specId)) {
        if (status.stats.completed > pw.previousCompleted) {
          // Read actual status from implementation_plan.json instead of hardcoding
          const actualStatus = this.readPlanStatus(specId, pw) ?? 'human_review';
          this.sendStatusChange(specId, actualStatus, pw.projectId);
        } else {
          this.sendStatusChange(specId, 'error', pw.projectId);
        }
      }
    }

    // Cleanup tasks no longer running in daemon
    for (const specId of [...pw.watchedTasks]) {
      if (!currentIds.has(specId)) {
        fileWatcher.unwatch(specId);
        pw.watchedTasks.delete(specId);
        daemonManagedTasks.delete(specId);
      }
    }

    // Update state for next comparison
    pw.previousRunningIds = currentIds;
    pw.previousCompleted = status.stats.completed;
  }

  private sendExecutionProgress(specId: string, info: DaemonTaskInfo, projectId?: string): void {
    if (!this.getMainWindow) return;
    safeSendToRenderer(
      this.getMainWindow,
      IPC_CHANNELS.TASK_EXECUTION_PROGRESS,
      specId,
      {
        phase: info.phase,
        currentSubtask: info.current_subtask || null,
        session: info.session || 1,
      },
      projectId,
    );
  }

  private readPlanStatus(specId: string, pw: ProjectWatcher): string | null {
    // Construct plan path: daemon_status.json is in .auto-claude/, specs are in .auto-claude/specs/
    const autoClaudeDir = path.dirname(pw.statusFilePath);
    const planPath = path.join(autoClaudeDir, 'specs', specId, 'implementation_plan.json');
    try {
      if (!existsSync(planPath)) return null;
      const content = readFileSync(planPath, 'utf-8');
      const plan = JSON.parse(content);
      if (plan.xstateState === 'done' || plan.status === 'done') return 'done';
      if (plan.status) return plan.status;
    } catch {
      // Fall through
    }
    return null;
  }

  /**
   * Notify renderer that new specs were discovered by the daemon.
   * Sends 'specs:new-spec' IPC so the renderer refreshes the task list.
   * This is the daemon-side equivalent of FileWatcher's 'new-spec' event.
   */
  private notifyNewSpecs(pw: ProjectWatcher): void {
    if (!this.getMainWindow) return;
    const mainWindow = this.getMainWindow();
    if (!mainWindow) return;
    // Derive projectPath from daemon_status.json location
    const autoClaudeDir = path.dirname(pw.statusFilePath);
    const projectPath = path.dirname(autoClaudeDir);
    console.log(`[DaemonStatusWatcher] New specs detected, triggering task list refresh for project: ${pw.projectId}`);
    // Use the same IPC channel as FileWatcher to trigger loadTasks(forceRefresh: true)
    mainWindow.webContents.send('specs:new-spec', {
      projectPath,
      specId: '_daemon_refresh',
      specDir: '',
    });
  }

  /**
   * Connect to the daemon's WebSocket server for sub-second status updates.
   * WS messages trigger an immediate processFile re-read (file is authoritative).
   * Falls back to file polling if WebSocket is unavailable.
   */
  private connectWebSocket(pw: ProjectWatcher, port: number): void {
    // Avoid duplicate connections
    if (pw.ws) return;

    try {
      const ws = new WebSocket(`ws://127.0.0.1:${port}`);
      pw.wsPort = port;

      ws.onopen = () => {
        console.log(`[DaemonStatusWatcher] WebSocket connected to ws://127.0.0.1:${port}`);
        pw.ws = ws;
      };

      ws.onmessage = () => {
        // WS = push notification that status changed.
        // Re-read the authoritative file (daemon writes before broadcast).
        this.processFile(pw.statusFilePath, pw);
      };

      ws.onerror = () => {
        // Close event follows; cleanup happens there
      };

      ws.onclose = () => {
        console.log(`[DaemonStatusWatcher] WebSocket disconnected from port ${port}`);
        pw.ws = null;
        pw.wsPort = null;
      };
    } catch {
      // WebSocket not available in this runtime — file polling continues
    }
  }

  private sendStatusChange(specId: string, status: string, projectId?: string): void {
    if (!this.getMainWindow) return;
    console.log(`[DaemonStatusWatcher] Task ${specId} → ${status} (project: ${projectId || 'unknown'})`);
    safeSendToRenderer(
      this.getMainWindow,
      IPC_CHANNELS.TASK_STATUS_CHANGE,
      specId,
      status,
      projectId,
    );
  }
}

export const daemonStatusWatcher = new DaemonStatusWatcher();
