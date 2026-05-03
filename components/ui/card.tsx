import { HTMLAttributes } from "react";

export function Card({ className = "", style, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-xl border ${className}`}
      style={{
        backgroundColor: "var(--surface)",
        borderColor: "var(--border)",
        boxShadow: "var(--shadow)",
        ...style,
      }}
      {...props}
    />
  );
}
