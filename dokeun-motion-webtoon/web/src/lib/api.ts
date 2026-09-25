export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public extra: Record<string, unknown> = {}) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...init,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(init.headers || {}) },
    cache: "no-store",
  });
  if (res.ok) return (await res.json()) as T;
  let body: any = {};
  try { body = await res.json(); } catch { /* 본문 없음 */ }
  const detail = body?.detail && typeof body.detail === "object" ? body.detail : body;
  const message = detail?.message || (res.status === 401 ? "로그인이 필요합니다." : "방송부 장비에 잠시 문제가 생겼습니다.");
  throw new ApiError(res.status, detail?.code || String(res.status), message, detail);
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
};

export const VERDICT_TONE: Record<string, string> = {
  YES: "yes", NO: "no", IRRELEVANT: "irrelevant", UNRELEASED: "locked",
  UNCLEAR: "unclear", NEGATIVE_FORM: "unclear", UNCONFIRMED: "unclear", NO_RECORD: "unclear",
};

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString("ko-KR", { timeZone: "Asia/Seoul", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
