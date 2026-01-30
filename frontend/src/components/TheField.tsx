import { useState, useEffect, useCallback } from "react";
import * as api from "../services/api";
import type { Coordinate } from "../types";

interface Props {
  rootCoordinateId: string | null;
}

const STATUS_ICONS: Record<string, string> = {
  pending: "○",
  in_progress: "◐",
  review: "◑",
  completed: "●",
  failed: "✗",
  blocked: "⊘",
};

export function TheField({ rootCoordinateId }: Props) {
  const [tree, setTree] = useState<Map<string, Coordinate[]>>(new Map());
  const [root, setRoot] = useState<Coordinate | null>(null);

  const loadTree = useCallback(async (coordId: string) => {
    const coord = (await api.getCoordinate(coordId)) as Coordinate;
    setRoot(coord);
    const loadChildren = async (parentId: string) => {
      const children = (await api.getCoordinateChildren(parentId)) as Coordinate[];
      setTree((prev) => new Map(prev).set(parentId, children));
      await Promise.all(children.map((c) => loadChildren(c.id)));
    };
    await loadChildren(coordId);
  }, []);

  useEffect(() => {
    if (rootCoordinateId) loadTree(rootCoordinateId);
  }, [rootCoordinateId, loadTree]);

  if (!rootCoordinateId) {
    return (
      <div className="screen">
        <h2>The Field</h2>
        <p className="empty">Select an active show to view its coordinate tree.</p>
      </div>
    );
  }

  const renderCoord = (coord: Coordinate, depth: number = 0): React.ReactElement => {
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
