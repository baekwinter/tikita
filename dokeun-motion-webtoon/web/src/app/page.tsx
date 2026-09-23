"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Waveform from "@/components/Waveform";

const ERRORS: Record<string, string> = {
  guild: "도근도근 디스코드 서버 멤버만 참여할 수 있어요. 서버에 참가한 계정으로 로그인해 주세요.",
  state: "로그인이 만료되었어요. 다시 시도해 주세요.",
  token: "디스코드 인증에 실패했어요. 잠시 후 다시 시도해 주세요.",
};

export default function Landing() {
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get("error");
    if (code) setError(ERRORS[code] || "로그인에 실패했어요.");
    api.get("/api/me")
      .then(() => window.location.replace("/play"))
      .catch(() => setChecking(false));
  }, []);

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <span className="onair">ON AIR</span>
          도근고등학교 달빛 방송부
        </div>
      </header>
      <main className="landing">
        <div className="landing-card panel">
          <div className="panel-body">
            <div className="scene">
              <span className="scene-tag">CASE #01 · CONFIDENTIAL</span>
              <img src="/scene-default.svg" alt="달빛이 드는 학교 방송실" />
            </div>
            <div className="eyebrow">2026 추석 특별 방송 · YES/NO 탐정</div>
            <h1>고백이 잘못 송출되었습니다.</h1>
            <p>
              추석 특별 방송 도중, 예정에 없던 고백이 스피커로 흘러나왔습니다.
              누가 녹음했을까요? 누구에게 전하려던 마음이었을까요? 그리고 누가 이 고백을 방송에 송출했을까요?
            </p>
            <Waveform />
            {error && <div className="banner">{error}</div>}
            <a className="btn primary discord-btn" href="/api/auth/login" aria-disabled={checking}>
              디스코드로 로그인하고 수사 시작하기
            </a>
            <p className="footer-note">
              도근도근 디스코드 서버 멤버만 참여할 수 있습니다. 로그인 시 디스코드 사용자 ID·이름과 참여 서버 목록만 확인하며,
              게임 진행도 외의 개인 정보는 저장하지 않습니다. 이 이야기는 허구이며 실제 인물·관계와 무관합니다.
            </p>
          </div>
        </div>
      </main>
    </>
  );
}
