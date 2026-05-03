import { FieldScore } from "@/lib/api";

const CONF = {
  HIGH:   { badge: "badge-high", bar: "conf-high", label: "HIGH" },
  MEDIUM: { badge: "badge-med",  bar: "conf-med",  label: "MED"  },
  LOW:    { badge: "badge-low",  bar: "conf-low",  label: "LOW"  },
} as const;

type ConfKey = keyof typeof CONF;

export function EvidenceList({ field, label }: { field: FieldScore; label: string }) {
  if (field.value == null) return null;

  const conf = CONF[(field.confidence as ConfKey)] ?? CONF.LOW;
  const value = Array.isArray(field.value) ? field.value.join(", ") : String(field.value);

  return (
    <div
      className={`border-l-2 pl-4 py-2 ${conf.bar}`}
      style={{ borderLeftWidth: "2px" }}
    >
      <div className="flex items-start justify-between gap-4 min-w-0">
        {/* Label + value */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-0.5">
            <span
              className="text-xs font-medium uppercase tracking-wider"
              style={{ color: "var(--text-faint)", letterSpacing: "0.06em" }}
            >
              {label}
            </span>
            <span className={`text-xs px-1.5 py-px rounded font-mono-data font-medium ${conf.badge}`}>
              {conf.label}
            </span>
          </div>
          <div className="text-sm font-medium truncate" style={{ color: "var(--text)" }}>
            {value}
          </div>
          {field.reason && (
            <div className="text-xs mt-0.5 truncate" style={{ color: "var(--text-faint)" }}>
              {field.reason}
            </div>
          )}
        </div>
      </div>

      {/* Evidence sources */}
      {field.evidence.length > 0 && (
        <ul className="mt-2 space-y-1">
          {field.evidence.map((e, i) => (
            <li key={i} className="flex items-start gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
              <span
                className="font-mono-data shrink-0 px-1 py-px rounded text-xs"
                style={{ backgroundColor: "var(--bg-muted)", color: "var(--text-faint)", fontSize: "10px" }}
              >
                {e.source_tier}
              </span>
              {e.url ? (
                <a
                  href={e.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline underline-offset-2 hover:opacity-80 transition-opacity"
                  style={{ color: "var(--accent)" }}
                >
                  {e.source}
                </a>
              ) : (
                <span>{e.source}</span>
              )}
              {e.snippet && (
                <span className="truncate" style={{ color: "var(--text-faint)" }}>
                  — {e.snippet.slice(0, 100)}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
