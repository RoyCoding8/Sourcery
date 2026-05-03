import { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost";
}

export function Button({ className = "", variant = "primary", style, ...props }: ButtonProps) {
  const base = "inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-lg transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-40 disabled:cursor-not-allowed";

  const styles =
    variant === "primary"
      ? {
          backgroundColor: "var(--accent)",
          color: "var(--accent-text)",
          focusOutlineColor: "var(--accent)",
        }
      : {
          backgroundColor: "transparent",
          color: "var(--text-muted)",
        };

  return (
    <button
      className={`${base} ${className}`}
      style={{
        backgroundColor: styles.backgroundColor,
        color: styles.color,
        ...style,
      }}
      onMouseEnter={e => {
        if (!props.disabled) {
          e.currentTarget.style.backgroundColor =
            variant === "primary" ? "var(--accent-hover)" : "var(--bg-muted)";
        }
      }}
      onMouseLeave={e => {
        e.currentTarget.style.backgroundColor = styles.backgroundColor;
      }}
      {...props}
    />
  );
}
