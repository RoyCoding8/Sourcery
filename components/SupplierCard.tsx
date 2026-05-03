import { EvidenceList } from "@/components/EvidenceList";
import { Supplier, FieldScore } from "@/lib/api";

const FIELDS: [keyof Supplier, string][] = [
  ["canonical_supplier_name", "Name"],
  ["website",                 "Website"],
  ["country_region",          "Country / Region"],
  ["product_category",        "Product Category"],
  ["certifications",          "Certifications"],
  ["employee_count",          "Employees"],
];

export function SupplierCard({ supplier }: { supplier: Supplier }) {
  const nameField = supplier.canonical_supplier_name as FieldScore;
  const name = nameField?.value ? String(nameField.value) : "Unknown Supplier";

  return (
    <div
      className="rounded-xl border overflow-hidden"
      style={{
        backgroundColor: "var(--surface)",
        borderColor: "var(--border)",
        boxShadow: "var(--shadow)",
      }}
    >
      {/* Card header */}
      <div
        className="px-5 py-3.5 border-b flex items-center justify-between"
        style={{ backgroundColor: "var(--bg-subtle)", borderColor: "var(--border-subtle)" }}
      >
        <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
          {name}
        </h3>
        {supplier.website && (
          <a
            href={String((supplier.website as FieldScore).value)}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs flex items-center gap-1 transition-opacity hover:opacity-70"
            style={{ color: "var(--accent)" }}
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
            </svg>
            Visit
          </a>
        )}
      </div>

      {/* Fields */}
      <div className="px-5 py-4 space-y-3">
        {FIELDS.map(([k, label]) => {
          const f = supplier[k] as FieldScore;
          return f ? <EvidenceList key={k} field={f} label={label} /> : null;
        })}
      </div>

      {/* Notes */}
      {supplier.notes && (
        <div
          className="px-5 py-3 border-t text-xs italic"
          style={{ borderColor: "var(--border-subtle)", color: "var(--text-faint)" }}
        >
          {supplier.notes}
        </div>
      )}
    </div>
  );
}
