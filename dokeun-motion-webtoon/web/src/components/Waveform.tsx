// 장식용 음성 파형 (정적 SVG)
export default function Waveform() {
  const bars = [4, 9, 6, 14, 8, 18, 11, 22, 13, 8, 16, 26, 12, 7, 19, 10, 24, 15, 9, 5, 12, 20, 8, 14, 6, 10, 4];
  return (
    <svg className="wave" viewBox="0 0 270 34" preserveAspectRatio="none" aria-hidden="true">
      {bars.map((h, i) => (
        <rect key={i} x={i * 10 + 3} y={17 - h / 2} width="4" height={h} rx="2"
          fill={i % 7 === 3 ? "#d9a2a8" : "#8fb6ff"} opacity={0.35 + (h / 26) * 0.6} />
      ))}
    </svg>
  );
}
