/** @type {import('next').NextConfig} */
// 브라우저는 같은 도메인의 /api/* 로만 요청한다. Next 서버가 FastAPI 로 전달하므로
// 쿠키가 같은 출처로 유지되고 CORS 설정이 필요 없다.
const API_ORIGIN = process.env.API_ORIGIN || "http://127.0.0.1:8000";

module.exports = {
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
};
