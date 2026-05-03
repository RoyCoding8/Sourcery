"use client";

import { useRef, useState } from "react";
import { ProviderPicker } from "@/components/ProviderPicker";
import { SupplierCard } from "@/components/SupplierCard";
import { Button } from "@/components/ui/button";
import { PipelineProgress } from "@/components/PipelineProgress";
import { RunResult, runQuery } from "@/lib/api";

export function QueryForm() {
  const [query, setQuery] = useState("Top 5 semiconductor manufacturers in Taiwan");
  const [prov, setProv] = useState("");
  const [model, setModel] = useState("");
  const [result, setResult] = useState<RunResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inFlight = useRef(false);

  const submit = async () => {
    if (inFlight.current || !query.trim()) return;
    inFlight.current = true;
    setLoading(true); setError(""); setResult(null);
    try { setResult(await runQuery(query, prov || undefined, model || undefined)); }
    catch (e) { setError(e instanceof Error ? e.message : "Request failed"); }
    finally { inFlight.current = false; setLoading(false); }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
  };

  return (
    <div className="space-y-8">
      {/* Query input area */}
      <div
        className="rounded-xl border p-1"
        style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)", boxShadow: "var(--shadow-md)" }}
      >
        <textarea
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKey}
          rows={2}
          placeholder="Describe the suppliers you're looking for..."
          aria-label="Supplier query"
          className="w-full px-4 pt-3 pb-2 text-sm resize-none focus:outline-none rounded-lg"
          style={{
            backgroundColor: "transparent",
            color: "var(--text)",
            lineHeight: 1.6,
          }}
        />
        <div
          className="flex items-center justify-between px-3 pb-2 pt-1 border-t"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          <ProviderPicker onChange={(p, m) => { setProv(p); setModel(m); }} />
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono-data" style={{ color: "var(--text-faint)" }}>
              Ctrl+↵
            </span>
            <Button onClick={submit} disabled={loading || !query.trim()}>
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                  </svg>
                  Searching
                </span>
              ) : "Search"}
            </Button>
          </div>
        </div>
      </div>

      {/* Pipeline progress */}
      <PipelineProgress active={loading} />

      {/* Error */}
      {error && (
        <div
          className="flex items-start gap-3 px-4 py-3 rounded-lg border text-sm"
          style={{ backgroundColor: "var(--low-bg)", borderColor: "var(--low-border)", color: "var(--low-text)" }}
          role="alert"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mt-0.5 shrink-0" aria-hidden="true">
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </div>
      )}

      {/* Partial warning */}
      {result?.partial && (
        <div
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg border text-xs"
          style={{ backgroundColor: "var(--med-bg)", borderColor: "var(--med-border)", color: "var(--med-text)" }}
          role="status"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          Partial results — some sources timed out.
        </div>
      )}

      {/* Results */}
      {result && (
        <div>
          <div className="flex items-baseline justify-between mb-5">
            <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              {result.suppliers.length} supplier{result.suppliers.length !== 1 ? "s" : ""} found
            </h2>
            <span className="text-xs font-mono-data" style={{ color: "var(--text-faint)" }}>
              {result.query}
            </span>
          </div>
          <div className="space-y-4">
            {result.suppliers.map((s, i) => (
              <div
                key={i}
                className={`animate-fade-up animate-fade-up-delay-${Math.min(i + 1, 5)}`}
              >
                <SupplierCard supplier={s} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
