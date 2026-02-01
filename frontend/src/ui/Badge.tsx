import type { ReactNode } from "react";

interface BadgeProps {
  variant?: "default" | "success" | "warning" | "danger" | "info";
  children: ReactNode;
  className?: string;
}

const VARIANT_CLASS: Record<string, string> = {
  default: "",
  success: "active",
  warning: "review",
  danger: "failed",
  info: "completed",
};

export function Badge({ variant = "default", children, className }: BadgeProps) {
  return (
    <span className={`badge ${VARIANT_CLASS[variant] || ""} ${className || ""}`}>
      {children}
    </span>
  );
}
