/**
 * Metrics Dashboard — Live visualization of swarm performance metrics.
 * Placeholder — redirects to Performance Explorer.
 */

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

const MetricsDashboard = () => {
  const navigate = useNavigate();
  useEffect(() => { navigate("/metrics", { replace: true }); }, [navigate]);
  return <div className="page-loading">Redirecting to Performance Explorer...</div>;
};

export default MetricsDashboard;
