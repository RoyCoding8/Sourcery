import { QueryForm } from "@/components/QueryForm";

export default function Home() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-16">
      {/* Hero */}
      <div className="mb-12">
        <p
          className="text-xs font-mono-data font-medium tracking-widest uppercase mb-4"
          style={{ color: "var(--accent)" }}
        >
          Supply Chain Intelligence
        </p>
        <h1
          className="text-3xl font-semibold tracking-tight mb-3"
          style={{ color: "var(--text)", lineHeight: 1.2 }}
        >
          Find suppliers you can trust
        </h1>
        <p className="text-sm max-w-lg" style={{ color: "var(--text-muted)", lineHeight: 1.6 }}>
          Describe what you're looking for. We'll check GLEIF, MOEA, TWSE, OFAC, and other registries — then tell you exactly how confident we are in each result.
        </p>
      </div>

      <QueryForm />
    </div>
  );
}
