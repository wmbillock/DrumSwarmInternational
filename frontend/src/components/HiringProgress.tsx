import { useEffect, useState } from "react";
import * as v1 from "../services/v1";
import "../styles/HiringProgress.css";

export function HiringProgress({ corpsId }: { corpsId: string }) {
  const [status, setStatus] = useState<v1.StaffingStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const res = await v1.getStaffingStatus(corpsId);
        if (mounted) setStatus(res);
      } catch (err) {
        if (mounted) setError(err instanceof Error ? err.message : "Failed to load staffing status");
      }
    };
    load();
    const interval = setInterval(load, 2000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [corpsId]);

  if (error) return <div className="hiring-error">{error}</div>;
  if (!status) return <div className="hiring-loading">Loading staffing status...</div>;

  const pct = status.total_roles > 0 ? Math.round((status.hired / status.total_roles) * 100) : 0;

  return (
    <div className="hiring-progress">
      <div className="hiring-header">
        <span className="hiring-title">Staffing Progress</span>
        <span className="hiring-count">
          {status.hired}/{status.total_roles}
        </span>
      </div>
      <div className="hiring-bar">
        <div className="hiring-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="hiring-meta">
        <span>{pct}% staffed</span>
        <span className="hiring-role">
          {status.current_role ? `Hiring: ${status.current_role.replace(/_/g, " ")}` : "Staffing complete"}
        </span>
      </div>
    </div>
  );
}
