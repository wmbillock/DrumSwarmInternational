import { Badge } from "../../ui";

export interface AlertItem {
  id: string;
  title: string;
  detail?: string;
  status: "good" | "warning" | "critical";
}

const statusVariant = (status: AlertItem["status"]) => {
  switch (status) {
    case "good":
      return "success";
    case "warning":
      return "warning";
    case "critical":
      return "danger";
    default:
      return "default";
  }
};

interface AlertPanelProps {
  title?: string;
  alerts: AlertItem[];
}

export function AlertPanel({ title, alerts }: AlertPanelProps) {
  return (
    <div className="alert-panel">
      {title && <div className="metrics-label" style={{ marginBottom: 8 }}>{title}</div>}
      {alerts.length === 0 && <p className="empty">No alerts.</p>}
      {alerts.map(alert => (
        <div key={alert.id} className="alert-row">
          <Badge variant={statusVariant(alert.status)}>{alert.status}</Badge>
          <div>
            <div className="alert-title">{alert.title}</div>
            {alert.detail && <div className="alert-detail">{alert.detail}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}
