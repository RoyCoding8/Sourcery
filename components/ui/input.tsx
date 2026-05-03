import { InputHTMLAttributes } from "react";

export function Input({ className = "", style, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`px-3 py-2 rounded-lg border text-sm w-full transition-colors focus:outline-2 focus:outline-offset-1 ${className}`}
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
