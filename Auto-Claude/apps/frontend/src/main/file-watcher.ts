import chokidar, { FSWatcher } from 'chokidar';
import { readFileSync, existsSync } from 'fs';
import path from 'path';
import { EventEmitter } from 'events';
import type { ImplementationPlan } from '../shared/types';

interface WatcherInfo {
  taskId: string;
  watcher: FSWatcher;
  planPath: string;
}

interface SpecsFolderWatcher {
  projectPath: string;
  watcher: FSWatcher;
}

/**
 * Watches implementation_plan.json files for real-time progress updates
 * Also watches specs folders for new spec creation
 */
export class FileWatcher extends EventEmitter {
  private watchers: Map<string, WatcherInfo> = new Map();
  private specsFolderWatchers: Map<string, SpecsFolderWatcher> = new Map();

  /**
   * Start watching a task's implementation plan
   */
  async watch(taskId: string, specDir: string): Promise<void> {
    // Stop any existing watcher for this task
    await this.unwatch(taskId);

    const planPath = path.join(specDir, 'implementation_plan.json');

    // Check if plan file exists
    if (!existsSync(planPath)) {
      this.emit('error', taskId, `Plan file not found: ${planPath}`);
      return;
    }

    // Create watcher with settings to handle frequent writes
    const watcher = chokidar.watch(planPath, {
      persistent: true,
      ignoreInitial: true,
      awaitWriteFinish: {
        stabilityThreshold: 300,
        pollInterval: 100
      }
    });

    // Store watcher info
    this.watchers.set(taskId, {
      taskId,
      watcher,
      planPath
    });

    // Handle file changes
    watcher.on('change', () => {
      try {
        const content = readFileSync(planPath, 'utf-8');
        const plan: ImplementationPlan = JSON.parse(content);
        this.emit('progress', taskId, plan);
      } catch {
        // File might be in the middle of being written
        // Ignore parse errors, next change event will have complete file
      }
    });

    // Handle errors
    watcher.on('error', (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error);
      this.emit('error', taskId, message);
    });

    // Read and emit initial state
    try {
      const content = readFileSync(planPath, 'utf-8');
      const plan: ImplementationPlan = JSON.parse(content);
      this.emit('progress', taskId, plan);
    } catch {
      // Initial read failed - not critical
    }
  }

  /**
   * Stop watching a task
   */
  async unwatch(taskId: string): Promise<void> {
    const watcherInfo = this.watchers.get(taskId);
    if (watcherInfo) {
      await watcherInfo.watcher.close();
      this.watchers.delete(taskId);
    }
  }

  /**
   * Watch a project's specs folder for new spec creation
   * Emits 'new-spec' event when a new spec folder is created
   */
  async watchSpecsFolder(projectPath: string): Promise<void> {
    // Stop any existing watcher for this project
    await this.unwatchSpecsFolder(projectPath);

    const specsPath = path.join(projectPath, '.auto-claude', 'specs');

    // Check if specs folder exists
    if (!existsSync(specsPath)) {
      console.log(`[FileWatcher] Specs folder not found: ${specsPath}`);
      return;
    }

    // Watch for new directories in specs folder
    const watcher = chokidar.watch(specsPath, {
      persistent: true,
      ignoreInitial: true,
      depth: 1, // Only watch immediate children
      awaitWriteFinish: {
        stabilityThreshold: 500,
        pollInterval: 100
      }
    });

    this.specsFolderWatchers.set(projectPath, {
      projectPath,
      watcher
    });

    // Handle new spec folder creation
    watcher.on('addDir', (dirPath: string) => {
      // Only emit for direct children of specs folder
      const parentDir = path.dirname(dirPath);
      if (path.normalize(parentDir) === path.normalize(specsPath)) {
        const specId = path.basename(dirPath);
        console.log(`[FileWatcher] New spec folder detected: ${specId}`);
        this.emit('new-spec', projectPath, specId, dirPath);
      }
    });

    // Also watch for implementation_plan.json creation in new specs
    watcher.on('add', (filePath: string) => {
      if (path.basename(filePath) === 'implementation_plan.json') {
        const specDir = path.dirname(filePath);
        const specId = path.basename(specDir);
        console.log(`[FileWatcher] New spec plan detected: ${specId}`);
        this.emit('new-spec-plan', projectPath, specId, specDir);
      }
    });

    watcher.on('error', (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error);
      console.error(`[FileWatcher] Specs folder watch error: ${message}`);
    });

    console.log(`[FileWatcher] Watching specs folder: ${specsPath}`);
  }

  /**
   * Stop watching a project's specs folder
   */
  async unwatchSpecsFolder(projectPath: string): Promise<void> {
    const watcherInfo = this.specsFolderWatchers.get(projectPath);
    if (watcherInfo) {
      await watcherInfo.watcher.close();
      this.specsFolderWatchers.delete(projectPath);
    }
  }

  /**
   * Stop all watchers (both task watchers and specs folder watchers)
   */
  async unwatchAll(): Promise<void> {
    // Close task watchers
    const taskClosePromises = Array.from(this.watchers.values()).map(
      async (info) => {
        await info.watcher.close();
      }
    );

    // Close specs folder watchers
    const specsClosePromises = Array.from(this.specsFolderWatchers.values()).map(
      async (info) => {
        await info.watcher.close();
      }
    );

    await Promise.all([...taskClosePromises, ...specsClosePromises]);
    this.watchers.clear();
    this.specsFolderWatchers.clear();
  }

  /**
   * Check if a task is being watched
   */
  isWatching(taskId: string): boolean {
    return this.watchers.has(taskId);
  }

  /**
   * Get current plan state for a task
   */
  getCurrentPlan(taskId: string): ImplementationPlan | null {
    const watcherInfo = this.watchers.get(taskId);
    if (!watcherInfo) return null;

    try {
      const content = readFileSync(watcherInfo.planPath, 'utf-8');
      return JSON.parse(content);
    } catch {
      return null;
    }
  }
}

// Singleton instance
export const fileWatcher = new FileWatcher();
