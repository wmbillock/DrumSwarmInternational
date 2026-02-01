import React, { useEffect, useState, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import "../styles/MessageInbox.css";

interface ThreadWithPreview extends v1.MessagingThread {
  unread?: boolean;
}

export default function MessageInbox() {
  const [threads, setThreads] = useState<ThreadWithPreview[]>([]);
  const [selectedThread, setSelectedThread] = useState<v1.MessagingThread | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("pending");
  const [replyContent, setReplyContent] = useState("");
  const [isReplying, setIsReplying] = useState(false);
  const [userRole, setUserRole] = useState("admin"); // In real app, get from auth context
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Load threads
  useEffect(() => {
    loadThreads();
  }, [statusFilter]);

  const loadThreads = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await v1.listMessagingThreads(statusFilter, undefined, 50, 0);
      setThreads((result.threads || []) as ThreadWithPreview[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load threads");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  // Load thread detail when selected
  const handleSelectThread = useCallback(async (threadId: string) => {
    try {
      const thread = await v1.getMessagingThread(threadId);
      setSelectedThread(thread);
      setReplyContent("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load thread");
    }
  }, []);

  // Add reply to thread
  const handleReply = useCallback(async () => {
    if (!selectedThread || !replyContent.trim()) return;

    setIsReplying(true);
    try {
      await v1.addMessageToThread(
        selectedThread.thread_id,
        "user",
        "User",
        replyContent,
        "user"
      );
      setReplyContent("");
      // Reload the thread
      await handleSelectThread(selectedThread.thread_id);
      // Reload thread list
      await loadThreads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send reply");
    } finally {
      setIsReplying(false);
    }
  }, [selectedThread, replyContent, userRole, handleSelectThread, loadThreads]);

  // Mark thread complete
  const handleMarkComplete = useCallback(async () => {
    if (!selectedThread) return;

    try {
      await v1.markThreadComplete(
        selectedThread.thread_id,
        userRole,
        "current-user-id"
      );
      // Reload the thread
      await handleSelectThread(selectedThread.thread_id);
      // Reload thread list
      await loadThreads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to mark thread complete");
    }
  }, [selectedThread, userRole, handleSelectThread, loadThreads]);

  // Format date
  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString();
    } catch {
      return isoString;
    }
  };

  return (
    <div className="message-inbox">
      <div className="inbox-header">
        <h1>Message Inbox</h1>
      </div>

      {error && <div className="inbox-error">{error}</div>}

      <div className="inbox-container">
        {/* Left Sidebar - Thread List */}
        <div className="inbox-sidebar">
          <div className="sidebar-filters">
            <div className="filter-group">
              <label>Status:</label>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="pending">Pending</option>
                <option value="completed">Completed</option>
                <option value="">All</option>
              </select>
            </div>
          </div>

          <div className="thread-list">
            {loading ? (
              <div className="loading">Loading threads...</div>
            ) : threads.length === 0 ? (
              <div className="no-threads">No threads</div>
            ) : (
              threads.map((thread) => (
                <div
                  key={thread.thread_id}
                  className={`thread-row ${selectedThread?.thread_id === thread.thread_id ? "selected" : ""} ${
                    thread.status === "completed" ? "completed" : ""
                  }`}
                  onClick={() => handleSelectThread(thread.thread_id)}
                >
                  <div className="thread-subject">{thread.subject}</div>
                  <div className="thread-meta">
                    <span className="thread-role">{thread.originator_role}</span>
                    <span className="thread-time">{formatDate(thread.updated_at)}</span>
                  </div>
                  {thread.status === "completed" && <span className="status-badge completed">Completed</span>}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Center Pane - Thread Detail */}
        <div className="inbox-detail">
          {selectedThread ? (
            <>
              <div className="thread-header">
                <h2>{selectedThread.subject}</h2>
                <div className="thread-info">
                  <span>From: {selectedThread.originator_role}</span>
                  <span>Status: {selectedThread.status}</span>
                  <span>Created: {formatDate(selectedThread.created_at)}</span>
                </div>
              </div>

              <div className="thread-messages">
                {selectedThread.messages && selectedThread.messages.length > 0 ? (
                  selectedThread.messages.map((msg) => (
                    <div key={msg.message_id} className="message">
                      <div className="message-header">
                        <strong>{msg.sender_name}</strong>
                        <span className="message-role">({msg.sender_role})</span>
                        <span className="message-time">{formatDate(msg.created_at)}</span>
                      </div>
                      <div className="message-body">{msg.body}</div>
                    </div>
                  ))
                ) : (
                  <div className="no-messages">No messages yet</div>
                )}
              </div>

              <div className="thread-actions">
                {selectedThread.status === "pending" && (
                  <>
                    <div className="reply-box">
                      <textarea
                        value={replyContent}
                        onChange={(e) => setReplyContent(e.target.value)}
                        placeholder="Type your reply..."
                        rows={3}
                      />
                      <div className="reply-buttons">
                        <button onClick={handleReply} disabled={isReplying || !replyContent.trim()}>
                          {isReplying ? "Sending..." : "Send Reply"}
                        </button>
                        <button onClick={handleMarkComplete} className="btn-complete">
                          Mark Complete
                        </button>
                      </div>
                    </div>
                  </>
                )}
                {selectedThread.status === "completed" && (
                  <div className="completed-info">
                    Thread completed on {formatDate(selectedThread.completed_at || "")}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="no-selection">Select a thread to view details</div>
          )}
        </div>
      </div>
    </div>
  );
}
