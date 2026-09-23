"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { EvidenceItem, GameState } from "@/lib/types";
import TopBar from "@/components/TopBar";
import CasePanel from "@/components/CasePanel";
import StatusCard from "@/components/StatusCard";
import Interrogation from "@/components/Interrogation";
import EvidencePanel from "@/components/EvidencePanel";
import FinalPanel from "@/components/FinalPanel";
import Modal from "@/components/Modal";

export default function Play() {
  const [state, setState] = useState<GameState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState(0);
  const [evidence, setEvidence] = useState<EvidenceItem | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const s = await api.get<GameState>("/api/state");
      setState(s);
      setSelected((cur) => (cur && cur <= s.case.current_episode ? cur : s.case.current_episode));
      return s;
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) { window.location.replace("/"); return null; }
      setError(e instanceof ApiError ? e.message : "수사실에 연결하지 못했어요.");
      return null;
    }
  }, []);

  useEffect(() => {
    load().then(async (s) => {
      if (s && s.case.phase === "live" && !s.progress.registered) {
        const r = await api.post<{ gained: number }>("/api/join").catch(() => null);
        if (r?.gained) showToast(`특별 조사원 등록 완료 · +${r.gained}점`);
        load();
      }
    });
    const timer = setInterval(load, 60_000); // 새 회차·증거 공개 반영
    return () => clearInterval(timer);
  }, [load]);

  const showToast = (t: string) => {
    setToast(t);
    setTimeout(() => setToast(null), 2600);
  };

  const openEvidence = async (id: string) => {
    try {
      const data = await api.post<EvidenceItem>(`/api/evidence/${id}/investigate`);
      setEvidence(data);
      if (data.new) showToast(`증거 ${data.id} 확보 · +${data.gained ?? 0}점`);
      load();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "증거를 열지 못했어요.");
    }
  };

  const markWatched = async (n: number) => {
    try {
      const r = await api.post<{ gained: number }>(`/api/episodes/${n}/watched`);
      showToast(`EP.${String(n).padStart(2, "0")} 시청 기록${r.gained ? ` · +${r.gained}점` : ""}`);
      load();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "기록하지 못했어요.");
    }
  };

  if (error && !state) return <main className="landing"><div className="banner">{error}</div></main>;
  if (!state) return <main className="landing"><div className="small">사건 파일을 여는 중…</div></main>;

  const phase = state.case.phase;
  const disabled =
    phase === "before" ? `이벤트는 ${state.case.start_at_kst}(한국 시간)에 시작됩니다.` :
    phase === "paused" ? "방송부가 잠시 방송을 점검하고 있습니다." : null;

  return (
    <>
      <TopBar state={state} />
      <main className="shell">
        {disabled && <div className="banner">{disabled}</div>}
        {phase === "ended" && <div className="banner">12화의 방송이 모두 끝났습니다. 디스코드 이벤트 채널에서 엔딩을 확인하세요.</div>}
        <div className="grid">
          <div className="col">
            <div className="slot s-case"><CasePanel state={state} selected={selected} onSelect={setSelected} onWatched={markWatched} /></div>
            <div className="slot s-evidence"><EvidencePanel items={state.evidence} onOpen={openEvidence} /></div>
          </div>
          <div className="col">
            <div className="slot s-status"><StatusCard state={state} /></div>
            <div className="slot s-ask"><Interrogation state={state} disabled={disabled} onAsked={() => load()} onOpenEvidence={openEvidence} onToast={showToast} /></div>
            <div className="slot s-final"><FinalPanel state={state} disabled={disabled} onDone={() => load()} onToast={showToast} /></div>
          </div>
        </div>
      </main>

      {evidence && (
        <Modal title={`${evidence.id} · ${evidence.title}`} eyebrow={`${evidence.category} · EP.${String(evidence.episode).padStart(2, "0")}`} onClose={() => setEvidence(null)}>
          {evidence.image_url && <img src={evidence.image_url} alt={evidence.title} />}
          <p className="detail">{evidence.detail}</p>
          <div className="row">{evidence.tags?.map((t) => <span key={t} className="tag muted">#{t}</span>)}</div>
          <p className="small" style={{ marginTop: 14 }}>증거 {evidence.id}이(가) 수사 수첩에 기록되었습니다.</p>
        </Modal>
      )}
      {toast && <div className="toast" role="status">{toast}</div>}
    </>
  );
}
