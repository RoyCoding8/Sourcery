import { SelectHTMLAttributes } from "react";

export function Select({ className = "", style, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`px-3 py-2 rounded-lg border text-sm transition-colors focus:outline-2 focus:outline-offset-1 ${className}`}
      style={{
        backgroundColor: "var(--surface)",
        borderColor: "var(--border)",
        color: "var(--text)",
        outlineColor: "var(--accent)",
        ...style,
      }}
      {...props}
    />
  );
}
