import type { ReactNode } from "react";

interface PanelProps {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Panel({ title, actions, children, className }: PanelProps) {
  return (
    <div className={`ui-panel ${className || ""}`}>
      {(title || actions) && (
        <div className="ui-panel-header">
          {title && <h3 className="ui-panel-title">{title}</h3>}
          {actions && <div className="ui-panel-actions">{actions}</div>}
        </div>
      )}
      <div className="ui-panel-body">{children}</div>
    </div>
  );
}
