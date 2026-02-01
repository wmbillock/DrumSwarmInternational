import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
}

export function Card({ children, onClick, className }: CardProps) {
  return (
    <div
      className={`card ${onClick ? "clickable" : ""} ${className || ""}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
