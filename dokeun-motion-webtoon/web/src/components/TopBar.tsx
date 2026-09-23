"use client";

import type { GameState } from "@/lib/types";
import { api } from "@/lib/api";

export default function TopBar({ state }: { state: GameState }) {
  const { case: c, progress: p, user } = state;
  const live = c.phase === "live";
  const logout = async () => { await api.post("/api/auth/logout").catch(() => null); window.location.href = "/"; };
  return (
    <header className="topbar">
      <div className="brand">
        <span className={`onair ${live ? "" : "off"}`}>ON AIR</span>
        달빛 방송부 수사실 <small className="hide-sm">고백이 잘못 송출되었습니다</small>
      </div>
      <div className="chips">
        <span className="chip">ROUND <b>{String(c.current_episode).padStart(2, "0")}/{c.total_episodes}</b></span>
        <span className="chip"><b>{p.questions.total}</b> 문</span>
        <span className="chip hide-sm">증거 <b>{p.evidence_found}/{p.evidence_released}</b></span>
        <span className="chip pink"><b>{p.points}</b> 점</span>
        <span className="user">
          {user.avatar && <img src={user.avatar} alt="" />}
          <span className="hide-sm">{user.name}</span>
          <button className="linkbtn" onClick={logout}>로그아웃</button>
        </span>
      </div>
    </header>
  );
}
