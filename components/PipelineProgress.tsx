"use client";

import { useEffect, useState } from "react";

const STAGES = [
  { label: "Parsing query",          pct: 8,   ms: 0     },
  { label: "Generating candidates",  pct: 25,  ms: 3000  },
  { label: "Resolving entities",     pct: 40,  ms: 8000  },
  { label: "Gathering evidence",     pct: 70,  ms: 15000 },
  { label: "Scoring confidence",     pct: 90,  ms: 35000 },
  { label: "Finalizing results",     pct: 96,  ms: 50000 },
];

export function PipelineProgress({ active }: { active: boolean }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!active) { setElapsed(0); return; }
    const start = Date.now();
    const id = setInterval(() => setElapsed(Date.now() - start), 200);
    return () => clearInterval(id);
  }, [active]);

  if (!active) return null;

  const stage = [...STAGES].reverse().find(s => elapsed >= s.ms) ?? STAGES[0];
  const nextStage = STAGES[STAGES.indexOf(stage) + 1];
  const stageProgress = nextStage
    ? stage.pct + ((nextStage.pct - stage.pct) * Math.min(1, (elapsed - stage.ms) / (nextStage.ms - stage.ms)))
    : stage.pct;
  const pct = Math.min(stageProgress, 96);

  return (
    <div className="space-y-2" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} aria-label="Pipeline progress">
      {/* Bar */}
      <div className="h-1 rounded-full overflow-hidden" style={{ backgroundColor: "var(--bg-muted)" }}>
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct}%`,
            backgroundColor: "var(--accent)",
            transition: "width 0.4s ease-out",
          }}
        />
      </div>
      {/* Stage label */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
          {stage.label}
        </span>
        <span className="text-xs font-mono-data" style={{ color: "var(--text-faint)" }}>
          {Math.floor(elapsed / 1000)}s
        </span>
      </div>
    </div>
  );
}
