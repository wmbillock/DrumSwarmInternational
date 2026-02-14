import { useState, useEffect, useCallback, useRef } from "react";
import * as v1 from "../services/v1";

const STORAGE_KEY = "dci-active-operations";
const POLL_INTERVAL = 3000; // 3 seconds

/** Persists active operation IDs to localStorage so they survive navigation. */
function loadTracked(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveTracked(ids: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
}

export interface UseOperationsResult {
  /** All currently tracked operations (pending/running/recently completed). */
  operations: v1.V1Operation[];
  /** Start tracking a new operation by ID (called after API returns operation_id). */
  track: (operationId: string) => void;
  /** Check if a specific target has an active (pending/running) operation. */
  isActive: (targetType: string, targetId: string) => boolean;
  /** Get the latest operation for a target (any status). */
  getLatest: (targetType: string, targetId: string) => v1.V1Operation | undefined;
  /** Dismiss a completed/failed operation from the tracked list. */
  dismiss: (operationId: string) => void;
  /** Number of currently active (pending/running) operations. */
  activeCount: number;
}

export function useOperations(): UseOperationsResult {
  const [operations, setOperations] = useState<v1.V1Operation[]>([]);
  const trackedRef = useRef<string[]>(loadTracked());

  const track = useCallback((operationId: string) => {
    if (!trackedRef.current.includes(operationId)) {
      trackedRef.current = [...trackedRef.current, operationId];
      saveTracked(trackedRef.current);
    }
  }, []);

  const dismiss = useCallback((operationId: string) => {
    trackedRef.current = trackedRef.current.filter((id) => id !== operationId);
    saveTracked(trackedRef.current);
    setOperations((prev) => prev.filter((op) => op.id !== operationId));
  }, []);

  // Poll tracked operations + server-side active operations
  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      if (cancelled) return;
      try {
        // Fetch server-side active operations
        const serverActive = await v1.getActiveOperations();

        // Also fetch any locally-tracked operations that might have completed
        const localIds = trackedRef.current;
        const serverIds = new Set(serverActive.map((op) => op.id));
        const missingIds = localIds.filter((id) => !serverIds.has(id));

        const fetched: v1.V1Operation[] = [];
        for (const id of missingIds) {
          try {
            const op = await v1.getOperation(id);
            fetched.push(op);
            // Clean up completed/failed ops from localStorage after 60s
            if (
              op.status === "completed" || op.status === "failed"
            ) {
              const completedAt = op.completed_at ? new Date(op.completed_at).getTime() : 0;
              if (Date.now() - completedAt > 60000) {
                trackedRef.current = trackedRef.current.filter((tid) => tid !== id);
                saveTracked(trackedRef.current);
              }
            }
          } catch {
            // Operation not found — remove from tracking
            trackedRef.current = trackedRef.current.filter((tid) => tid !== id);
            saveTracked(trackedRef.current);
          }
        }

        if (!cancelled) {
          // Merge: server active + locally tracked
          const allOps = [...serverActive, ...fetched];
          // Deduplicate by ID
          const seen = new Set<string>();
          const unique = allOps.filter((op) => {
            if (seen.has(op.id)) return false;
            seen.add(op.id);
            return true;
          });
          setOperations(unique);

          // Track any server-side active operations we don't know about
          for (const op of serverActive) {
            if (!trackedRef.current.includes(op.id)) {
              trackedRef.current = [...trackedRef.current, op.id];
            }
          }
          saveTracked(trackedRef.current);
        }
      } catch {
        // Silently fail — will retry next interval
      }
    };

    poll();
    const interval = setInterval(poll, POLL_INTERVAL);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const isActive = useCallback(
    (targetType: string, targetId: string) =>
      operations.some(
        (op) =>
          op.target_type === targetType &&
          op.target_id === targetId &&
          (op.status === "pending" || op.status === "running"),
      ),
    [operations],
  );

  const getLatest = useCallback(
    (targetType: string, targetId: string) =>
      operations.find(
        (op) => op.target_type === targetType && op.target_id === targetId,
      ),
    [operations],
  );

  const activeCount = operations.filter(
    (op) => op.status === "pending" || op.status === "running",
  ).length;

  return { operations, track, isActive, getLatest, dismiss, activeCount };
}
