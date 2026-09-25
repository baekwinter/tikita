export type Verdict = "YES" | "NO" | "IRRELEVANT" | "UNRELEASED" | "UNCLEAR" | "NEGATIVE_FORM" | "UNCONFIRMED" | "NO_RECORD";

export interface EpisodeInfo {
  number: number;
  code: string;
  title: string;
  description: string | null;
  keywords: string[];
  has_thumbnail: boolean;
  thumbnail_url?: string | null;
  video_url: string | null;
  discord_link: string | null;
  released_at: string | null;
}

export interface CaseInfo {
  bot_name: string;
  title: string;
  summary: string;
  phase: "before" | "live" | "paused" | "ended";
  start_at: string;
  start_at_kst: string;
  current_episode: number;
  total_episodes: number;
  episode: EpisodeInfo | null;
  episodes: EpisodeInfo[];
  next_episode: { number: number; at_kst: string; at: string | null } | null;
  characters: string[];
}

export interface Quota { limit: number; used: number; remaining: number; total: number; }

export interface Progress {
  registered: boolean;
  status: string;
  current_episode: number;
  total_episodes: number;
  watched: number[];
  evidence_found: number;
  evidence_released: number;
  evidence_total: number;
  questions: Quota;
  theories: number;
  final_attempts: number;
  final_max_attempts: number;
  points: number;
  currency: string;
}

export interface EvidenceItem {
  id: string;
  episode: number;
  locked: boolean;
  title?: string;
  category?: string;
  summary?: string;
  detail?: string;
  tags?: string[];
  found?: boolean;
  has_image?: boolean;
  image_url?: string;
  new?: boolean;
  gained?: number;
}

export interface HistoryItem { asked_at: string; question: string; verdict: Verdict; label: string; }

export interface AskResult {
  question: string;
  verdict: Verdict;
  label: string;
  hint: string;
  response_text: string;
  matched: string | null;
  related_evidence: { id: string; title: string } | null;
  counted: boolean;
  duplicate: boolean;
  gained: number;
  quota: Quota;
}

export interface FinalFormItem { key: string; label: string; type: "choice" | "text"; choices?: string[]; }

export interface FinalStatus {
  open: boolean;
  open_from_episode: number;
  attempts: number;
  max_attempts: number;
  feedback: "count" | "sealed";
  solved: boolean;
  ended: boolean;
  form: FinalFormItem[];
  last: null | { submitted_at: string; answers: Record<string, string>; correct?: number; total?: number; items?: Record<string, boolean> };
}

export interface FinalResult {
  saved: boolean;
  gained: number;
  attempts: number;
  max_attempts: number;
  correct?: number;
  total?: number;
  solved?: boolean;
  items?: Record<string, boolean>;
}

export interface GameState {
  user: { id: number; name: string; avatar: string | null };
  admin: boolean;
  case: CaseInfo;
  progress: Progress;
  evidence: EvidenceItem[];
  history: HistoryItem[];
  final: FinalStatus;
  note: { body: string; updated_at: string | null };
}
