import type { GameState } from "@/lib/types";

export default function StatusCard({ state }: { state: GameState }) {
  const p = state.progress;
  const q = p.questions;
  const pct = q.limit ? Math.min(100, (q.used / q.limit) * 100) : 0;
  return (
    <section className="panel" aria-label="수사 현황">
      <div className="panel-body">
        <div className="stat-top">
          <div>
            <div className="eyebrow">자유 수사 · 오늘의 질문</div>
            <div className="stat-big">{q.used}<span>/{q.limit}</span></div>
          </div>
          <div className="small" style={{ textAlign: "right" }}>
            남은 질문 <b style={{ color: "var(--moon)" }}>{q.remaining}</b><br />매일 0시에 충전
          </div>
        </div>
        <div className="bar"><i style={{ width: `${pct}%` }} /></div>
        <div className="stat-row">
          <div className="stat"><div className="k">확보 증거</div><div className="v">{p.evidence_found}/{p.evidence_released}</div></div>
          <div className="stat"><div className="k">추리 시도</div><div className="v">{p.theories + p.final_attempts}</div></div>
          <div className="stat"><div className="k">{p.currency}</div><div className="v">{p.points}</div></div>
        </div>
      </div>
    </section>
  );
}
