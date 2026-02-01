import { useState, useEffect, useCallback } from "react";
import * as v1 from "../services/v1";
import type { Segment } from "../types";

interface Props {
  rootSegmentId: string | null;
}

const STATUS_ICONS: Record<string, string> = {
  pending: "○",
  in_progress: "◐",
  review: "◑",
  completed: "●",
  failed: "✗",
  blocked: "⊘",
};

export function TheField({ rootSegmentId }: Props) {
  const [tree, setTree] = useState<Map<string, Segment[]>>(new Map());
  const [root, setRoot] = useState<Segment | null>(null);

  const loadTree = useCallback(async (coordId: string) => {
    const coord = (await v1.getSegment(coordId)) as Segment;
    setRoot(coord);
    const loadChildren = async (parentId: string) => {
      const children = (await v1.getSegmentChildren(parentId)) as Segment[];
      setTree((prev) => new Map(prev).set(parentId, children));
      await Promise.all(children.map((c) => loadChildren(c.id)));
    };
    await loadChildren(coordId);
  }, []);

  useEffect(() => {
    if (rootSegmentId) loadTree(rootSegmentId);
  }, [rootSegmentId, loadTree]);

  if (!rootSegmentId) {
    return (
      <div className="screen">
        <h2>The Field</h2>
        <p className="empty">Select an active show to view its segment tree.</p>
      </div>
    );
  }

  const renderCoord = (coord: Segment, depth: number = 0): React.ReactElement => {
    const children = tree.get(coord.id) || [];
    return (
      <div key={coord.id} className="coord-node" style={{ marginLeft: depth * 20 }}>
        <div className={`coord-card status-${coord.status}`}>
          <span className="coord-icon">{STATUS_ICONS[coord.status] || "?"}</span>
          <span className="coord-type">{coord.type}</span>
          <span className="coord-title">{coord.title}</span>
          {coord.caption && <span className="badge caption">{coord.caption}</span>}
          <span className={`badge ${coord.status}`}>{coord.status}</span>
        </div>
        {children.map((c) => renderCoord(c, depth + 1))}
      </div>
    );
  };

  return (
    <div className="screen">
      <h2>The Field</h2>
      <p className="subtitle">Show &rarr; movement &rarr; segment &rarr; set tree with status</p>
      {root && renderCoord(root)}
    </div>
  );
}
