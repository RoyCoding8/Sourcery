"use client";

import { useEffect, useState } from "react";
import { Select } from "@/components/ui/select";
import { Provider, fetchProviders } from "@/lib/api";

export function ProviderPicker({ onChange }: { onChange: (p: string, m: string) => void }) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [prov, setProv] = useState("");
  const [model, setModel] = useState("");

  useEffect(() => { fetchProviders().then(setProviders); }, []);

  const models = providers.find(p => p.name === prov)?.models ?? [];
  const pickProv = (v: string) => {
    const m = providers.find(p => p.name === v)?.models[0] ?? "";
    setProv(v); setModel(m); onChange(v, m);
  };
  const pickModel = (v: string) => { setModel(v); onChange(prov, v); };

  return (
    <div className="flex gap-3 items-center">
      <Select value={prov} onChange={e => pickProv(e.target.value)} aria-label="LLM Provider">
        <option value="">Provider...</option>
        {providers.filter(p => p.available).map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
      </Select>
      {models.length > 0 && <Select value={model} onChange={e => pickModel(e.target.value)} aria-label="Model">
        {models.map(m => <option key={m} value={m}>{m}</option>)}
      </Select>}
    </div>
  );
}
