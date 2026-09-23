"use client";

import { useState } from "react";
import type { GameState } from "@/lib/types";
import Modal from "./Modal";

export default function CasePanel({ state, selected, onSelect, onWatched }: {
  state: GameState; selected: number; onSelect: (n: number) => void; onWatched: (n: number) => void;
}) {
  const c = state.case;
  const ep = c.episodes.find((e) => e.number === selected) || c.episode;
  const [zoom, setZoom] = useState(false);
  const image = ep?.thumbnail_url || "/scene-default.svg";
  const watched = new Set(state.progress.watched);
  const videoLink = ep?.discord_link || ep?.video_url;

  return (
    <section className="panel" aria-label="사건 파일">
      <div className="scene">
        <span className="scene-tag">CASE #01 · CONFIDENTIAL{ep ? ` · ${ep.code}` : ""}</span>
        <img src={image} alt={ep ? `${ep.title} 장면` : "달빛이 드는 학교 방송실"} />
        <button className="scene-zoom" onClick={() => setZoom(true)}>확대</button>
      </div>

      <div className="case-copy">
        <div className="eyebrow">사건명</div>
        <h1 className="case-title">{c.title}</h1>
        <p className="case-summary">{c.summary}</p>
        <div className="row">
          {c.characters.map((name) => <span key={name} className="tag pink">{name}</span>)}
        </div>

        {ep ? (
          <div className="ep-line">
            <span className="ep-name">{ep.title}</span>
            {ep.keywords.map((k) => <span key={k} className="tag">{k}</span>)}
            {watched.has(ep.number) ? <span className="tag muted">시청 완료</span> : null}
            <span style={{ flex: 1 }} />
            {videoLink && <a className="btn inline ghost" href={videoLink} target="_blank" rel="noreferrer">영상 보기</a>}
            {!watched.has(ep.number) && (
              <button className="btn inline" onClick={() => onWatched(ep.number)}>시청 완료</button>
            )}
          </div>
        ) : (
          <div className="ep-line small">아직 공개된 회차가 없습니다.</div>
        )}
        {ep?.description && <p className="case-summary" style={{ marginTop: 10 }}>{ep.description}</p>}
      </div>

      <div className="episodes" role="list" aria-label="회차">
        {Array.from({ length: c.total_episodes }, (_, i) => i + 1).map((n) => {
          const open = n <= c.current_episode;
          const next = c.next_episode?.number === n;
          return (
            <button key={n} role="listitem" disabled={!open}
              className={`ep ${selected === n ? "active" : ""} ${watched.has(n) ? "watched" : ""}`}
              onClick={() => open && onSelect(n)} title={open ? `EP.${n} 보기` : "미공개"}>
              EP.{String(n).padStart(2, "0")}
              <span className="dot">{open ? (watched.has(n) ? "시청" : "공개") : next ? c.next_episode?.at_kst : "잠김"}</span>
            </button>
          );
        })}
      </div>

      {zoom && (
        <Modal title={ep?.title || c.title} eyebrow="SCENE" onClose={() => setZoom(false)}>
          <img src={image} alt="" />
        </Modal>
      )}
    </section>
  );
}
