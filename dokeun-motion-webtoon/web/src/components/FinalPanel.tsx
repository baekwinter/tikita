"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { FinalResult, GameState } from "@/lib/types";
import Modal from "./Modal";

export default function FinalPanel({ state, disabled, onDone, onToast }: {
  state: GameState; disabled: string | null; onDone: () => void; onToast: (t: string) => void;
}) {
  const f = state.final;
  const [open, setOpen] = useState(false);
  const left = f.max_attempts - f.attempts;
  const blocked = disabled || (!f.open ? `EP.${String(f.open_from_episode).padStart(2, "0")} 공개 후 제출할 수 있어요.` : null)
    || (f.solved ? "사건의 진실에 도달했습니다." : null) || (left <= 0 ? "제출 기회를 모두 사용했습니다." : null);

  return (
    <section className="panel" aria-label="최종 추리">
      <div className="composer" style={{ borderTop: 0 }}>
        <div className="label red">정답 제출하기 <small>남은 기회 {Math.max(0, left)} / {f.max_attempts}</small></div>
        <p className="small" style={{ margin: "0 0 4px" }}>
          범인의 이름만으로는 부족합니다. 누가 녹음했고, 누구를 향했고, 누가 어떻게·왜 송출했는지까지 밝혀야 사건 해결입니다.
        </p>
        {f.last && f.last.correct !== undefined && (
          <div className="notice ok">마지막 제출: 5문항 중 {f.last.correct}개 정답</div>
        )}
        <button className="btn danger" disabled={!!blocked} onClick={() => setOpen(true)}>
          {blocked || "질문 끝내기 · 최종 추리 제출"}
        </button>
      </div>
      {open && <FinalDialog state={state} onClose={() => setOpen(false)} onDone={onDone} onToast={onToast} />}
    </section>
  );
}

function FinalDialog({ state, onClose, onDone, onToast }: {
  state: GameState; onClose: () => void; onDone: () => void; onToast: (t: string) => void;
}) {
  const f = state.final;
  const [answers, setAnswers] = useState<Record<string, string>>({ q1: "", q2: "", q3: "", q4: "", q5: "", story: "" });
  const [step, setStep] = useState<"form" | "confirm" | "result">("form");
  const [result, setResult] = useState<FinalResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const set = (k: string, v: string) => setAnswers((a) => ({ ...a, [k]: v }));
  const ready = ["q1", "q2", "q3", "q4"].every((k) => answers[k]) && answers.q5.trim().length >= 10;

  const submit = async () => {
    setBusy(true); setError(null);
    try {
      const r = await api.post<FinalResult>("/api/final", answers);
      setResult(r); setStep("result");
      if (r.gained) onToast(`+${r.gained} 달빛 수사 포인트`);
      onDone();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "제출하지 못했어요."); setStep("form");
    } finally { setBusy(false); }
  };

  return (
    <Modal title="최종 추리" eyebrow="FINAL REPORT" onClose={onClose}>
      {step === "form" && (
        <>
          {f.form.map((item) => (
            <div key={item.key} className="q-block">
              <div className="ql"><b>{item.key === "story" ? "+" : item.key.toUpperCase()}</b>{item.label}</div>
              {item.type === "choice" ? (
                <div className="choices" role="radiogroup" aria-label={item.label}>
                  {item.choices!.map((c) => (
                    <button key={c} role="radio" aria-checked={answers[item.key] === c}
                      className={`choice ${answers[item.key] === c ? "on" : ""}`} onClick={() => set(item.key, c)}>{c}</button>
                  ))}
                </div>
              ) : (
                <textarea className="input" rows={item.key === "q5" ? 3 : 4} maxLength={1500} value={answers[item.key]}
                  placeholder={item.key === "q5" ? "왜 그렇게 했는지, 어떤 방법으로 했는지 한두 문장으로 적어 주세요." : "2025년과 2026년에 각각 무슨 일이 있었는지 정리해 보세요."}
                  onChange={(e) => set(item.key, e.target.value)} />
              )}
            </div>
          ))}
          {error && <div className="notice">{error}</div>}
          <button className="btn danger" disabled={!ready} onClick={() => setStep("confirm")}>
            {ready ? "제출 전 확인" : "Q1~Q4 선택과 Q5 작성(10자 이상)이 필요해요"}
          </button>
        </>
      )}
      {step === "confirm" && (
        <>
          <p>이대로 제출할까요? 제출하면 기회가 1회 차감됩니다. (남은 기회 {f.max_attempts - f.attempts}회)</p>
          <ul className="small">
            {["q1", "q2", "q3", "q4"].map((k) => <li key={k}>{k.toUpperCase()} · {answers[k]}</li>)}
          </ul>
          <div className="row">
            <button className="btn ghost inline" onClick={() => setStep("form")}>다시 고치기</button>
            <button className="btn danger inline" disabled={busy} onClick={submit}>{busy ? "제출 중…" : "최종 제출"}</button>
          </div>
        </>
      )}
      {step === "result" && result && (
        <div className="result">
          {result.correct !== undefined ? (
            <>
              <div className="eyebrow">채점 결과</div>
              <div className="score">{result.correct}/{result.total}</div>
              <p>{result.solved ? "사건의 진실에 도달했습니다. 엔딩 공개를 기다려 주세요." : "아직 맞지 않는 조각이 있어요. 증거와 질문으로 다시 확인해 보세요."}</p>
            </>
          ) : (
            <p>최종 추리가 접수되었습니다. 채점 결과는 엔딩 공개 때 발표됩니다.</p>
          )}
          <p className="small">제출 {result.attempts}/{result.max_attempts}회</p>
          <button className="btn" onClick={onClose}>닫기</button>
        </div>
      )}
    </Modal>
  );
}
