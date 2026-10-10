"""멤버별 히어로 효과(얼굴 원 주변 CSS 연출)와 상징 문양 SVG.

토큰: __A__ = 포인트 컬러 hex / __RGB__ = 포인트 컬러 r,g,b / __LRGB__ = 밝은 틴트 r,g,b
얼굴 원(.nx-disc)과 컨테이너(.nx-orb)는 base.css 공통. 여기서는 그 주변 레이어만 정의한다.
before = 얼굴 원 뒤 레이어, after = 얼굴 원 위 레이어.
"""

HERO_FX = {
    # 심연 — 바깥에서 안쪽으로 빨려 들어가는 파문 (침잠)
    "abyss": {
        "before": '<div class="nx-deep"></div><i class="nx-rip"></i><i class="nx-rip nx-rip--2"></i><i class="nx-rip nx-rip--3"></i>',
        "after": "",
        "css": """
  .nx-deep{position:absolute;inset:-48px;border-radius:50%;background:radial-gradient(circle,rgba(__RGB__,.28) 0%,rgba(__RGB__,.08) 45%,transparent 70%);filter:blur(6px)}
  .nx-rip{position:absolute;inset:0;border-radius:50%;border:1px solid rgba(__LRGB__,.7);opacity:.35;transform:scale(1.12);animation:nx-sink 7.5s cubic-bezier(.3,.1,.3,1) infinite}
  .nx-rip--2{opacity:.2;transform:scale(1.28);animation-delay:-2.5s}.nx-rip--3{opacity:.1;transform:scale(1.45);animation-delay:-5s}
  @keyframes nx-sink{0%{transform:scale(1.6);opacity:0}35%{opacity:.55}100%{transform:scale(1);opacity:0}}
""",
    },
    # 일식 — reference 그대로: 회전하는 코로나 + 다이아몬드 링 플레어
    "eclipse": {
        "before": '<div class="nx-corona"></div>',
        "after": '<div class="nx-flare"></div>',
        "css": """
  .nx-corona{position:absolute;inset:-34px;border-radius:50%;
    background:conic-gradient(from 0deg,transparent 0%,rgba(__RGB__,.75) 8%,transparent 22%,rgba(__LRGB__,.5) 38%,transparent 52%,rgba(__RGB__,.65) 70%,transparent 84%,rgba(__LRGB__,.4) 94%,transparent 100%);
    filter:blur(16px);animation:nx-spin 22s linear infinite}
  .nx-flare{position:absolute;top:20px;right:24px;z-index:2;width:14px;height:14px;border-radius:50%;background:#fff6e4;
    box-shadow:0 0 12px 4px rgba(255,240,215,.9),0 0 40px 12px rgba(__RGB__,.5);animation:nx-pulse 4.5s ease-in-out infinite}
  @keyframes nx-spin{to{transform:rotate(360deg)}}
  @keyframes nx-pulse{0%,100%{opacity:.55;transform:scale(.8)}50%{opacity:1;transform:scale(1.15)}}
""",
    },
    # 혜성 — 기울어진 궤도선 + 얼굴 원 가장자리를 스치는 꼬리별
    "comet": {
        "before": '<div class="nx-path"></div>',
        "after": '<i class="nx-tail"></i><i class="nx-tail nx-tail--2"></i>',
        "css": """
  .nx-path{position:absolute;inset:-18px -54px;border-radius:50%;border:1px solid rgba(__RGB__,.22);transform:rotate(-28deg)}
  .nx-tail{position:absolute;left:50%;top:50%;z-index:2;width:150px;height:2px;margin:-1px 0 0 -75px;border-radius:2px;
    background:linear-gradient(90deg,transparent,rgba(__RGB__,.5) 55%,rgba(__LRGB__,.95));opacity:0;animation:nx-comet 7s ease-in infinite}
  .nx-tail::after{content:"";position:absolute;right:-4px;top:-3px;width:8px;height:8px;border-radius:50%;background:#fff;box-shadow:0 0 10px 3px rgba(__RGB__,.95),0 0 26px 8px rgba(__RGB__,.4)}
  .nx-tail--2{width:90px;margin-left:-45px;animation-delay:-3.5s;animation-duration:9s}
  @keyframes nx-comet{0%{transform:rotate(-28deg) translate(-260px,-108px);opacity:0}6%{opacity:1}34%{transform:rotate(-28deg) translate(230px,-108px);opacity:0}100%{transform:rotate(-28deg) translate(230px,-108px);opacity:0}}
""",
    },
    # 안개 — 얼굴 원 위로 흐린 안개 띠 3장이 좌우로 흐른다
    "mist": {
        "before": '<div class="nx-haze"></div>',
        "after": '<i class="nx-fog"></i><i class="nx-fog nx-fog--2"></i><i class="nx-fog nx-fog--3"></i>',
        "css": """
  .nx-haze{position:absolute;inset:-40px;border-radius:50%;background:radial-gradient(circle,rgba(__RGB__,.22),transparent 68%);filter:blur(10px)}
  .nx-fog{position:absolute;z-index:2;left:-38%;width:176%;height:30%;top:16%;border-radius:50%;pointer-events:none;
    background:radial-gradient(ellipse at center,rgba(__LRGB__,.2),rgba(__LRGB__,.05) 55%,transparent 72%);filter:blur(12px);animation:nx-drift 13s ease-in-out infinite alternate}
  .nx-fog--2{top:48%;height:26%;animation-duration:17s;animation-direction:alternate-reverse}
  .nx-fog--3{top:72%;height:34%;animation-duration:21s;animation-delay:-6s}
  @keyframes nx-drift{from{transform:translateX(-14%)}to{transform:translateX(14%)}}
""",
    },
    # 달 — 일정 간격의 얇은 달무리 링이 숨 쉬듯 밝아진다 (트랙 02 '달무리')
    "moon": {
        "before": '<div class="nx-glow"></div><i class="nx-halo"></i><i class="nx-halo nx-halo--2"></i><i class="nx-halo nx-halo--3"></i>',
        "after": "",
        "css": """
  .nx-glow{position:absolute;inset:-30px;border-radius:50%;background:radial-gradient(circle,rgba(__LRGB__,.24) 40%,transparent 70%);filter:blur(12px)}
  .nx-halo{position:absolute;inset:-16px;border-radius:50%;border:1px solid rgba(__LRGB__,.5);animation:nx-breathe 6s ease-in-out infinite}
  .nx-halo--2{inset:-32px;border-color:rgba(__LRGB__,.3);animation-delay:-2s}
  .nx-halo--3{inset:-48px;border-color:rgba(__LRGB__,.16);animation-delay:-4s}
  @keyframes nx-breathe{0%,100%{opacity:.35;transform:scale(.985)}50%{opacity:1;transform:scale(1.015)}}
""",
    },
    # 오로라 — 얼굴 원 뒤로 물결치는 빛의 커튼, 명도가 천천히 바뀐다
    "aurora": {
        "before": '<i class="nx-aur"></i><i class="nx-aur nx-aur--2"></i>',
        "after": "",
        "css": """
  .nx-aur{position:absolute;inset:-46px -64px;border-radius:42%;filter:blur(18px);opacity:.7;
    background:repeating-linear-gradient(98deg,transparent 0 9%,rgba(__RGB__,.6) 15%,transparent 22%,rgba(__LRGB__,.42) 28%,transparent 35%);
    animation:nx-aurora 11s ease-in-out infinite alternate}
  .nx-aur--2{inset:-30px -40px;opacity:.5;animation-duration:15s;animation-direction:alternate-reverse}
  @keyframes nx-aurora{0%{transform:skewX(-14deg) scaleY(.82) translateX(-7%);opacity:.35}50%{opacity:.85}100%{transform:skewX(14deg) scaleY(1.08) translateX(7%);opacity:.5}}
""",
    },
    # 별 — 얼굴 원 주변 별빛 7개가 시차를 두고 반짝인다
    "star": {
        "before": '<div class="nx-dust"></div>',
        "after": "".join(f'<i class="nx-spk nx-spk--{i}"></i>' for i in range(1, 8)),
        "css": """
  .nx-dust{position:absolute;inset:-36px;border-radius:50%;background:radial-gradient(circle,rgba(__RGB__,.26),transparent 66%);filter:blur(8px)}
  .nx-spk{position:absolute;z-index:2;width:16px;height:16px;margin:-8px 0 0 -8px;opacity:.2;filter:drop-shadow(0 0 4px rgba(__RGB__,.95));
    background:radial-gradient(circle,#fff 0 1.6px,transparent 2.4px),linear-gradient(transparent,rgba(__LRGB__,.95),transparent) center/1.5px 100% no-repeat,linear-gradient(90deg,transparent,rgba(__LRGB__,.95),transparent) center/100% 1.5px no-repeat;
    animation:nx-twinkle 3.4s ease-in-out infinite}
  .nx-spk--1{top:-4%;left:22%}.nx-spk--2{top:6%;left:94%;animation-delay:-.5s;width:22px;height:22px;margin:-11px 0 0 -11px}
  .nx-spk--3{top:40%;left:-10%;animation-delay:-1s}.nx-spk--4{top:64%;left:108%;animation-delay:-1.5s}
  .nx-spk--5{top:100%;left:76%;animation-delay:-2s;width:22px;height:22px;margin:-11px 0 0 -11px}.nx-spk--6{top:98%;left:14%;animation-delay:-2.5s}
  .nx-spk--7{top:-12%;left:66%;animation-delay:-3s;width:12px;height:12px;margin:-6px 0 0 -6px}
  @keyframes nx-twinkle{0%,100%{opacity:.15;transform:scale(.5) rotate(0)}50%{opacity:1;transform:scale(1.1) rotate(45deg)}}
""",
    },
}

_S = 'fill="none" stroke="currentColor" stroke-width="1.4"'
EMBLEM_BODY = {
    # 안쪽으로 말려 들어가는 동심원 3개
    "abyss": f'<circle cx="20" cy="18" r="15" {_S}/><circle cx="20" cy="21.5" r="10" {_S}/><circle cx="20" cy="25" r="5" {_S}/><circle cx="20" cy="27" r="1.8" fill="currentColor"/>',
    # 원 위에 반쯤 겹친 검은 원 + 우상단의 작은 빛점 (reference 원본)
    "eclipse": f'<circle cx="19" cy="21" r="13" {_S}/><circle cx="22.5" cy="18.5" r="11" fill="#07070a" stroke="currentColor" stroke-width="1.4"/><circle cx="33" cy="7" r="2.4" fill="currentColor"/>',
    # 사선으로 길게 끌리는 꼬리 + 머리 쪽 점
    "comet": f'<path d="M4 36 27.5 12.5" {_S}/><path d="M6 28 25 11" {_S} opacity=".6"/><path d="M12 34 29 15" {_S} opacity=".6"/><circle cx="30.5" cy="9.5" r="3.6" fill="currentColor"/>',
    # 수평으로 흐르는 물결선 3줄
    "mist": f'<path d="M4 13q4-4 8 0t8 0 8 0 8 0" {_S}/><path d="M8 21q4-4 8 0t8 0 8 0" {_S}/><path d="M4 29q4-4 8 0t8 0 8 0 8 0" {_S}/>',
    # 초승달 + 바깥을 감싼 얇은 링(달무리)
    "moon": f'<circle cx="20" cy="20" r="17" {_S} stroke-dasharray="2 2.6"/><circle cx="20" cy="20" r="10" fill="currentColor"/><circle cx="24.5" cy="16.5" r="8.6" fill="#07070a"/>',
    # 세로로 일렁이는 파형 커튼 3줄
    "aurora": f'<path d="M10 5q-4 7.5 0 15t0 15" {_S}/><path d="M20 5q4 7.5 0 15t0 15" {_S}/><path d="M30 5q-4 7.5 0 15t0 15" {_S}/>',
    # 네 갈래 빛이 교차하는 별
    "star": f'<path d="M20 3 22.8 17.2 37 20 22.8 22.8 20 37 17.2 22.8 3 20 17.2 17.2Z" {_S} stroke-linejoin="round"/><circle cx="20" cy="20" r="1.8" fill="currentColor"/>',
}

# 그룹 문양: 원(밤) 둘레 7개의 점, 그중 하나가 원 안쪽으로 떨어져 있다(낙화)
def _group_emblem_body():
    import math
    parts = [f'<circle cx="20" cy="20" r="14" {_S}/>']
    for i in range(7):
        a = math.radians(-90 + i * 360 / 7)
        x, y = 20 + 14 * math.cos(a), 20 + 14 * math.sin(a)
        if i == 4:  # 떨어진 점
            x, y = 20 + 6.5 * math.cos(a), 20 + 6.5 * math.sin(a)
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="currentColor"/>')
        else:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="currentColor"/>')
    return "".join(parts)

GROUP_EMBLEM_BODY = _group_emblem_body()


def emblem(mid, cls="nx-emb"):
    body = GROUP_EMBLEM_BODY if mid == "group" else EMBLEM_BODY[mid]
    return f'<svg class="{cls}" viewBox="0 0 40 40" aria-hidden="true">{body}</svg>'
