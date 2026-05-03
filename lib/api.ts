export type Provider = { name: string; models: string[]; available: boolean };
export type Evidence = { source: string; source_tier: string; url: string; snippet: string };
export type FieldScore = { value: unknown; confidence: string; reason: string; evidence: Evidence[] };
export type Supplier = Record<
  "canonical_supplier_name" | "website" | "country_region" | "product_category" | "certifications" | "employee_count",
  FieldScore
> & { notes: string };
export type RunResult = { query: string; suppliers: Supplier[]; partial: boolean };

const json = async <T>(url: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
};

export const fetchProviders = () => json<Provider[]>("/api/providers");

export const runQuery = (query: string, provider?: string, model?: string) =>
  json<RunResult>("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, provider, model }),
  });
