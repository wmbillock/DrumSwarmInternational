import { useState, useCallback } from "react";
import * as v1 from "../services/v1";
import "../styles/MessageArchive.css";
import { formatTimestamp } from "../utils/formatters";

export default function MessageArchive() {
  const [results, setResults] = useState<v1.ArchivedThreadSummary[]>([]);
  const [selectedArchive, setSelectedArchive] = useState<v1.ArchivedThreadSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [originatorRole, setOriginatorRole] = useState("");
  const [userRole] = useState("admin"); // In real app, get from auth context

  // Search archives
  const handleSearch = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await v1.searchArchive(
        searchQuery || undefined,
        originatorRole || undefined,
        50,
        0
      );
      setResults(result.archived_threads || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to search archive");
    } finally {
      setLoading(false);
    }
  }, [searchQuery, originatorRole]);

  // Load archived thread detail
  const handleSelectArchive = useCallback(async (archivedId: string) => {
    try {
      const archive = await v1.getArchivedThread(archivedId);
      setSelectedArchive(archive);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load archived thread");
    }
  }, []);

  const formatDate = (isoString: string) => formatTimestamp(isoString);

  // Check permissions
  const canAccessArchive =
    userRole === "admin" || userRole === "executive_director";

  if (!canAccessArchive) {
    return (
      <div className="page-content">
        <div className="page-header">
          <h2 className="page-title">Message Archive</h2>
        </div>
        <div className="error-banner">
          <p>Access denied. Only administrators and executive directors can access the archive.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content message-archive">
      <div className="archive-header page-header">
        <div>
          <h1 className="page-title">Message Archive</h1>
          <p>Search archived threads for historical context and decisions</p>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button className="small" style={{ marginLeft: 8 }} onClick={handleSearch}>Retry</button>
        </div>
      )}

      <div className="archive-container">
        {/* Left Pane - Search Interface */}
        <div className="archive-search">
          <div className="search-group">
            <label htmlFor="search">Search:</label>
            <input
              id="search"
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Keywords..."
              onKeyPress={(e) => e.key === "Enter" && handleSearch()}
            />
          </div>

          <div className="search-group">
            <label htmlFor="role">Originator Role:</label>
            <select
              id="role"
              value={originatorRole}
              onChange={(e) => setOriginatorRole(e.target.value)}
            >
              <option value="">All Roles</option>
              <option value="executive_director">Executive Director</option>
              <option value="program_coordinator">Program Coordinator</option>
              <option value="caption_head">Caption Head</option>
              <option value="tech">Tech</option>
              <option value="music_writer">Music Writer</option>
            </select>
          </div>

          <button onClick={handleSearch} disabled={loading} className="btn-search">
            {loading ? "Searching..." : "Search"}
          </button>

          <div className="results-list">
            {results.length === 0 && !loading && (
              <div className="no-results">No results found</div>
            )}
            {results.map((archive) => (
              <div
                key={archive.archived_thread_id}
                className={`result-item ${selectedArchive?.archived_thread_id === archive.archived_thread_id ? "selected" : ""}`}
                onClick={() => handleSelectArchive(archive.archived_thread_id)}
              >
                <div className="result-subject">{archive.subject}</div>
                <div className="result-meta">
                  <span className="result-role">{archive.originator_role}</span>
                  {(() => {
                    const ts = formatDate(archive.archived_at);
                    return <span className="result-date" title={ts.title}>{ts.label}</span>;
                  })()}
                </div>
                {archive.tags && archive.tags.length > 0 && (
                  <div className="result-tags">
                    {archive.tags.slice(0, 3).map((tag) => (
                      <span key={tag} className="tag">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right Pane - Archive Detail */}
        <div className="archive-detail">
          {selectedArchive ? (
            <>
              <div className="archive-header-detail">
                <h2>{selectedArchive.subject}</h2>
                <div className="archive-info">
                  <span>From: {selectedArchive.originator_role}</span>
                  <span>Messages: {selectedArchive.message_count}</span>
                  {(() => {
                    const ts = formatDate(selectedArchive.archived_at);
                    return <span title={ts.title}>Archived: {ts.label}</span>;
                  })()}
                </div>
              </div>

              <div className="archive-body">
                <h3>Summary</h3>
                <p>{selectedArchive.summary}</p>

                {selectedArchive.decision && (
                  <>
                    <h3>Decision</h3>
                    <p>{selectedArchive.decision}</p>
                  </>
                )}

                {selectedArchive.tags && selectedArchive.tags.length > 0 && (
                  <>
                    <h3>Tags</h3>
                    <div className="tags-display">
                      {selectedArchive.tags.map((tag) => (
                        <span key={tag} className="tag">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </>
                )}

                <div className="archive-metadata">
                  <p>
                    <strong>Original Thread ID:</strong> {selectedArchive.original_thread_id}
                  </p>
                  {(() => {
                    const ts = formatDate(selectedArchive.created_at);
                    return (
                      <p>
                        <strong>Created:</strong> <span title={ts.title}>{ts.label}</span>
                      </p>
                    );
                  })()}
                  {(() => {
                    const ts = formatDate(selectedArchive.archived_at);
                    return (
                      <p>
                        <strong>Archived:</strong> <span title={ts.title}>{ts.label}</span>
                      </p>
                    );
                  })()}
                </div>
              </div>
            </>
          ) : (
            <div className="no-selection">Select an archived thread to view details</div>
          )}
        </div>
      </div>
    </div>
  );
}
