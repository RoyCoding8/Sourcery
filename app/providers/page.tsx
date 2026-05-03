"use client";
import { useEffect, useState } from "react";
import { fetchProviders, Provider } from "@/lib/api";

export default function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);

  useEffect(() => { fetchProviders().then(setProviders); }, []);

  const available = providers.filter(p => p.available);
  const unavailable = providers.filter(p => !p.available);

  return (
    <div className="max-w-5xl mx-auto px-6 py-16">
      <div className="mb-10">
        <p
          className="text-xs font-mono-data font-medium tracking-widest uppercase mb-4"
          style={{ color: "var(--accent)" }}
        >
          Configuration
        </p>
        <h1 className="text-2xl font-semibold tracking-tight mb-2" style={{ color: "var(--text)" }}>
          LLM Providers
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Add your keys to <code className="font-mono-data text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: "var(--bg-muted)", color: "var(--text)" }}>.env</code> and they'll show up here as ready.
        </p>
      </div>

      {providers.length === 0 ? (
        <div className="text-sm" style={{ color: "var(--text-faint)" }}>Loading providers…</div>
      ) : (
        <div className="space-y-8">
          {available.length > 0 && (
            <section>
              <h2 className="text-xs font-medium uppercase tracking-wider mb-3" style={{ color: "var(--text-faint)" }}>
                Available
              </h2>
              <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--border)" }}>
                {available.map((p, i) => (
                  <ProviderRow key={p.name} provider={p} last={i === available.length - 1} />
                ))}
              </div>
            </section>
          )}

          {unavailable.length > 0 && (
            <section>
              <h2 className="text-xs font-medium uppercase tracking-wider mb-3" style={{ color: "var(--text-faint)" }}>
                Not configured
              </h2>
              <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--border)" }}>
                {unavailable.map((p, i) => (
                  <ProviderRow key={p.name} provider={p} last={i === unavailable.length - 1} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

function ProviderRow({ provider: p, last }: { provider: Provider; last: boolean }) {
  return (
    <div
      className={`flex items-center justify-between px-5 py-3.5 ${!last ? "border-b" : ""}`}
      style={{
        backgroundColor: "var(--surface)",
        borderColor: "var(--border-subtle)",
        opacity: p.available ? 1 : 0.5,
      }}
    >
      <div className="flex items-center gap-4 min-w-0">
        <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
          {p.name}
        </span>
        {p.models.length > 0 && (
          <span className="text-xs font-mono-data truncate" style={{ color: "var(--text-faint)" }}>
            {p.models.join(" · ")}
          </span>
        )}
      </div>
      <span
        className={`text-xs px-2 py-0.5 rounded font-medium shrink-0 ${p.available ? "badge-high" : ""}`}
        style={!p.available ? { backgroundColor: "var(--bg-muted)", color: "var(--text-faint)" } : {}}
      >
        {p.available ? "ready" : "no credentials"}
      </span>
    </div>
  );
}
