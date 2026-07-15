"use client";

/**
 * RagDashboard — RAG Pipeline management interface for admins.
 *
 * Provides Google Drive delta scanning, file-by-file sync execution,
 * progress tracking, and knowledge base statistics.
 */

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DeltaResponse, FileDelta, RagStats, SyncResult } from "@/lib/types";
import styles from "./rag-dashboard.module.scss";

export default function RagDashboard() {
  const [stats, setStats] = useState<RagStats | null>(null);
  const [delta, setDelta] = useState<DeltaResponse | null>(null);
  const [scanning, setScanning] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState({ current: 0, total: 0 });
  const [syncLog, setSyncLog] = useState<SyncResult[]>([]);

  // Load stats on mount
  useEffect(() => {
    const loadStats = async () => {
      try {
        const data = await api.getRagStats();
        setStats(data);
      } catch (error) {
        console.error("Failed to load RAG stats:", error);
      }
    };
    loadStats();
  }, []);

  const handleScan = useCallback(async () => {
    setScanning(true);
    setDelta(null);
    try {
      const data = await api.getRagDelta();
      setDelta(data);
    } catch (error) {
      console.error("Failed to scan delta:", error);
    } finally {
      setScanning(false);
    }
  }, []);

  const handleSyncAll = useCallback(async () => {
    if (!delta) return;

    const filesToSync: FileDelta[] = [...delta.new, ...delta.modified];
    const filesToDelete: FileDelta[] = delta.deleted;
    const total = filesToSync.length + filesToDelete.length;

    if (total === 0) return;

    setSyncing(true);
    setSyncProgress({ current: 0, total });
    setSyncLog([]);

    // Process deletions first
    for (const file of filesToDelete) {
      try {
        await api.deleteRagFile(file.gdrive_id);
        setSyncProgress((prev) => ({ ...prev, current: prev.current + 1 }));
      } catch (error) {
        console.error(`Failed to delete ${file.name}:`, error);
      }
    }

    // Process new and modified files one-by-one (O(1) memory footprint)
    for (const file of filesToSync) {
      try {
        const result = await api.syncFile(file.gdrive_id);
        setSyncLog((prev) => [...prev, result]);
        setSyncProgress((prev) => ({ ...prev, current: prev.current + 1 }));
      } catch (error) {
        console.error(`Failed to sync ${file.name}:`, error);
        setSyncProgress((prev) => ({ ...prev, current: prev.current + 1 }));
      }
    }

    setSyncing(false);
    setDelta(null);

    // Refresh stats
    try {
      const newStats = await api.getRagStats();
      setStats(newStats);
    } catch {
      // Non-critical
    }
  }, [delta]);

  const progressPercent =
    syncProgress.total > 0
      ? Math.round((syncProgress.current / syncProgress.total) * 100)
      : 0;

  return (
    <div className={styles.dashboard}>
      {/* Stats Overview */}
      <div className={styles.stats}>
        <div className={styles.statCard}>
          <span className={styles.statValue}>
            {stats?.total_files ?? "—"}
          </span>
          <span className={styles.statLabel}>Indexed Files</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statValue}>
            {stats?.total_chunks ?? "—"}
          </span>
          <span className={styles.statLabel}>Total Chunks</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statValue}>768</span>
          <span className={styles.statLabel}>Vector Dims</span>
        </div>
      </div>

      {/* Sync Controls */}
      <div className={styles.syncSection}>
        <div className={styles.syncHeader}>
          <h3 className={styles.syncTitle}>Knowledge Base Sync</h3>
          <button
            className={styles.scanBtn}
            onClick={handleScan}
            disabled={scanning || syncing}
            id="scan-delta-btn"
          >
            {scanning ? "Scanning..." : "Scan Google Drive"}
          </button>
        </div>

        {delta && (
          <div className={styles.deltaInfo}>
            <div className={styles.deltaRow}>
              <div className={styles.deltaLabel}>
                <div className={`${styles.deltaIcon} ${styles.deltaNew}`} />
                <span className={styles.deltaText}>New Files</span>
              </div>
              <span className={styles.deltaCount}>{delta.new.length}</span>
            </div>
            <div className={styles.deltaRow}>
              <div className={styles.deltaLabel}>
                <div className={`${styles.deltaIcon} ${styles.deltaModified}`} />
                <span className={styles.deltaText}>Modified Files</span>
              </div>
              <span className={styles.deltaCount}>{delta.modified.length}</span>
            </div>
            <div className={styles.deltaRow}>
              <div className={styles.deltaLabel}>
                <div className={`${styles.deltaIcon} ${styles.deltaDeleted}`} />
                <span className={styles.deltaText}>Deleted Files</span>
              </div>
              <span className={styles.deltaCount}>{delta.deleted.length}</span>
            </div>

            {delta.total_changes > 0 && (
              <button
                className={styles.syncAllBtn}
                onClick={handleSyncAll}
                disabled={syncing}
                id="sync-all-btn"
              >
                {syncing
                  ? `Syncing... (${syncProgress.current}/${syncProgress.total})`
                  : `Sync ${delta.total_changes} Changes`}
              </button>
            )}
          </div>
        )}

        {syncing && (
          <div className={styles.progress}>
            <div className={styles.progressBar}>
              <div
                className={styles.progressFill}
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <span className={styles.progressText}>
              Processing {syncProgress.current} of {syncProgress.total} files
              ({progressPercent}%)
            </span>
          </div>
        )}
      </div>

      {/* Indexed Files */}
      <div>
        <h3
          className={styles.syncTitle}
          style={{ marginBottom: "16px" }}
        >
          Indexed Files
        </h3>
        {stats?.files && stats.files.length > 0 ? (
          <div className={styles.fileList}>
            {stats.files.map((file) => (
              <div key={file.id} className={styles.fileItem}>
                <div className={styles.fileInfo}>
                  <span className={styles.fileName}>{file.name}</span>
                  <span className={styles.fileMeta}>
                    {file.mime_type} ·{" "}
                    {new Date(file.updated_at).toLocaleDateString("en-IN")}
                  </span>
                </div>
                <span className={styles.chunkBadge}>
                  {file.chunk_count} chunks
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.emptyState}>
            No files indexed yet. Scan Google Drive to get started.
          </div>
        )}
      </div>
    </div>
  );
}
