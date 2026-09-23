"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError, VERDICT_TONE, formatTime } from "@/lib/api";
import type { AskResult, GameState, HistoryItem } from "@/lib/types";

interface LogEntry { question: string; verdict: string; label: string; memo?: string; hint?: string; related?: { id: string; title: string } | null; at?: string; fresh?: boolean; }

const NOTE_KEY = "dalbit-note";

export default function Interrogation({ state, disabled, onAsked, onOpenEvidence, onToast }: {
  state: GameState; disabled: string | null;
  onAsked: (r: AskResult) => void; onOpenEvidence: (id: string) => void; onToast: (t: string) => void;
}) {
  const [tab, setTab] = useState<"log" | "note">("log");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [entries, setEntries] = useState<LogEntry[]>(() => toEntries(state.history));
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => { logRef.current?.scrollTo({ top: logRef.current.scrollHeight }); }, [entries.length, tab]);

  const ask = async () => {
    const q = text.trim();
    if (!q || busy || disabled) return;
    setBusy(true); setNotice(null);
    try {
      const r = await api.post<AskResult>("/api/ask", { text: q });
      setEntries((prev) => [...prev, {
        question: r.question, verdict: r.verdict, label: r.label, memo: r.response_text, hint: r.hint,
        related: r.related_evidence, fresh: true,
      }]);
      setText("");
      if (r.duplicate) setNotice("같은 질문은 질문 횟수에서 차감하지 않았어요.");
      else if (!r.counted) setNotice("해석하지 못한 질문은 횟수에서 차감하지 않아요.");
      if (r.gained) onToast(`+${r.gained} 달빛 수사 포인트`);
      onAsked(r);
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "질문을 보내지 못했어요.");
    } finally {
      setBusy(false);
    }
  };

  const q = state.progress.questions;

  return (
    <section className="panel" aria-label="방송부 심문">
      <div className="panel-head">
        <div className="head-left">
          <div className="seal" aria-hidden="true">月</div>
          <div>
            <div className="eyebrow">Interrogation</div>
            <h2 className="panel-title">방송부 심문</h2>
          </div>
        </div>
        <div className="count">{q.total}문<small>남은 질문 {q.remaining}</small></div>
      </div>

      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "log"} className={tab === "log" ? "on" : ""} onClick={() => setTab("log")}>
          현재 심문 {entries.length}
        </button>
        <button role="tab" aria-selected={tab === "note"} className={tab === "note" ? "on" : ""} onClick={() => setTab("note")}>
          수사 노트
        </button>
      </div>

      {tab === "log" ? (
        <>
          <div className="log" ref={logRef} aria-live="polite">
            {entries.length === 0 ? (
              <div className="empty">
                <p>무엇이든 물어보세요 · 단, 예/아니오로 답할 수 있는 것만.</p>
                <div className="small">예) 반휘혈이 고백을 녹음했나요? · 2025년에도 고백이 있었나요?</div>
                <div className="small" style={{ marginTop: 6 }}>YES · NO · 관계없음 · 아직 공개되지 않은 정보</div>
              </div>
            ) : entries.map((e, i) => (
              <div key={i} className={`qa ${e.fresh ? "just" : ""}`}>
                <div className="q">{e.question}</div>
                <div className="a">
                  <span className={`verdict ${VERDICT_TONE[e.verdict] || "unclear"}`}>{e.label}</span>
                  {e.related && (
                    <button className="linkbtn" onClick={() => onOpenEvidence(e.related!.id)}>관련 증거 {e.related.id} {e.related.title}</button>
                  )}
                  {e.at && <span className="small">{formatTime(e.at)}</span>}
                </div>
                {e.memo && <div className="memo">{e.memo}</div>}
                {e.hint && !e.memo && <div className="memo">{e.hint}</div>}
              </div>
            ))}
          </div>
          <div className="composer">
            <div className="label">질문하기 <small>Enter 로 보내기 · Shift+Enter 줄바꿈</small></div>
            <textarea className="input" value={text} maxLength={200} rows={2}
              placeholder={disabled || "예/아니오로 답할 수 있는 질문을 입력…"} disabled={!!disabled || busy}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); ask(); } }} />
            <button className="btn primary" onClick={ask} disabled={!!disabled || busy || !text.trim() || q.remaining <= 0}>
              {busy ? "방송부가 기록을 확인하는 중…" : q.remaining <= 0 ? "오늘의 질문을 모두 사용했어요" : "질문하기"}
            </button>
            {notice && <div className="notice">{notice}</div>}
          </div>
        </>
      ) : (
        <NotePad initial={state.note.body} updatedAt={state.note.updated_at} disabled={disabled} onToast={onToast} />
      )}
    </section>
  );
}

function toEntries(history: HistoryItem[]): LogEntry[] {
  return [...history].reverse().map((h) => ({ question: h.question, verdict: h.verdict, label: h.label, at: h.asked_at }));
}

function NotePad({ initial, updatedAt, disabled, onToast }: {
  initial: string; updatedAt: string | null; disabled: string | null; onToast: (t: string) => void;
}) {
  const [body, setBody] = useState(() => {
    if (typeof window === "undefined") return initial;
    const local = window.localStorage.getItem(NOTE_KEY);
    return local !== null && local.length >= initial.length ? local : initial;
  });
  const [saved, setSaved] = useState<string | null>(updatedAt);
  const [status, setStatus] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const change = (v: string) => {
    setBody(v);
    try { window.localStorage.setItem(NOTE_KEY, v); } catch { /* 저장 공간 없음 */ }
    setStatus("저장 중…");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      try {
        const r = await api.put<{ updated_at: string }>("/api/note", { body: v });
        setSaved(r.updated_at); setStatus("");
      } catch { setStatus("서버 저장 실패 · 이 기기에는 저장됨"); }
    }, 1200);
  };

  const submitTheory = async () => {
    try {
      const r = await api.post<{ count: number; gained: number }>("/api/theory", { body });
      onToast(r.gained ? `가설 제출 완료 · +${r.gained}점` : `가설 제출 완료 (누적 ${r.count}건)`);
    } catch (e) {
      onToast(e instanceof ApiError ? e.message : "제출하지 못했어요.");
    }
  };

  return (
    <div className="composer" style={{ borderTop: 0 }}>
      <div className="label">수사 노트 <small>{status || (saved ? `서버 저장 ${formatTime(saved)}` : "나만 볼 수 있어요")}</small></div>
      <textarea className="input" style={{ minHeight: 260 }} value={body} maxLength={5000}
        placeholder={"떠오른 단서와 가설을 자유롭게 적어 두세요.\n\n예) 2025년 답장은 왜 전달되지 않았을까?"}
        onChange={(e) => change(e.target.value)} />
      <button className="btn" onClick={submitTheory} disabled={!!disabled || body.trim().length < 5}>
        이 노트를 오늘의 가설로 제출
      </button>
    </div>
  );
}
