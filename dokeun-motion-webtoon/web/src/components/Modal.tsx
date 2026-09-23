"use client";

import { useEffect } from "react";

export default function Modal({ title, eyebrow, onClose, children }: {
  title: string; eyebrow?: string; onClose: () => void; children: React.ReactNode;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, [onClose]);
  return (
    <div className="overlay" onClick={onClose} role="presentation">
      <div className="modal" role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <div className="panel-head">
          <div>
            {eyebrow && <div className="eyebrow">{eyebrow}</div>}
            <h2 className="panel-title">{title}</h2>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="닫기">닫기</button>
        </div>
        <div className="panel-body">{children}</div>
      </div>
    </div>
  );
}
