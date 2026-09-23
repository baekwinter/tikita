"use client";

import type { EvidenceItem } from "@/lib/types";

export default function EvidencePanel({ items, onOpen }: { items: EvidenceItem[]; onOpen: (id: string) => void }) {
  const open = items.filter((e) => !e.locked).length;
  return (
    <section className="panel" aria-label="증거 목록">
      <div className="panel-head">
        <div>
          <div className="eyebrow">Evidence</div>
          <h2 className="panel-title">증거 보관함</h2>
        </div>
        <div className="small">공개 {open} / {items.length}</div>
      </div>
      <div className="evidence-grid">
        {items.map((e) => e.locked ? (
          <div key={e.id} className="card locked" aria-disabled="true">
            <span className="id">{e.id}</span>
            <span className="t">잠긴 증거</span>
            <span className="s">EP.{String(e.episode).padStart(2, "0")} 공개 후 열립니다.</span>
          </div>
        ) : (
          <button key={e.id} className="card" onClick={() => onOpen(e.id)}>
            <span className="id">{e.id} · {e.category}</span>
            <span className="t">{e.title}</span>
            <span className="s">{e.summary}</span>
            <span className="found">{e.found ? "수사 수첩에 기록됨" : "조사하기 →"}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
