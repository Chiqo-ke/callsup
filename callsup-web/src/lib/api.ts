/**
 * API client for all CALLSUP backend services.
 * Services run locally:
 *   Audio Engine       → http://127.0.0.1:8010
 *   Intelligence Engine → http://127.0.0.1:8011
 *   LLM Adapter        → http://127.0.0.1:9100
 */

export const SERVICES = {
  audio: "http://127.0.0.1:8010",
  intelligence: "http://127.0.0.1:8011",
  llm: "http://127.0.0.1:9100",
} as const;

export type ServiceName = keyof typeof SERVICES;
export type ServiceStatus = "online" | "offline" | "loading";

export interface HealthResult {
  service: ServiceName;
  status: ServiceStatus;
  version?: string;
}

export interface TranscriptSegment {
  speaker: string;
  text: string;
  start_ms: number;
  end_ms: number;
  confidence?: number;
}

export interface IntelligenceAction {
  action_type: string;
  response_text: string;
  tts: boolean;
  escalate: boolean;
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function fetchHealth(service: ServiceName): Promise<HealthResult> {
  try {
    const res = await fetch(`${SERVICES[service]}/health`, {
      signal: AbortSignal.timeout(4000),
    });
    if (!res.ok) return { service, status: "offline" };
    const body = await res.json();
    return { service, status: "online", version: body.version };
  } catch {
    return { service, status: "offline" };
  }
}

// ── Audio Engine ──────────────────────────────────────────────────────────────

export async function ingestAudio(
  businessId: string,
  convId: string,
  file: File
): Promise<{ status: string; conv_id: string }> {
  const form = new FormData();
  form.append("business_id", businessId);
  form.append("conv_id", convId);
  form.append("file", file);

  const res = await fetch(`${SERVICES.audio}/audio/ingest`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Ingest failed");
  }
  return res.json();
}

export async function simulateCall(
  businessId: string,
  convId: string,
  script: string
): Promise<{ status: string; conv_id: string; segments: number }> {
  const res = await fetch(`${SERVICES.audio}/audio/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ business_id: businessId, conv_id: convId, script }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Simulate failed");
  }
  return res.json();
}

export async function fetchTranscript(convId: string): Promise<TranscriptSegment[]> {
  const res = await fetch(`${SERVICES.audio}/audio/transcript/${encodeURIComponent(convId)}`);
  if (res.status === 404) throw new Error("Conversation not found");
  if (!res.ok) throw new Error(`Transcript request failed: ${res.status}`);
  return res.json();
}

// ── Voice conversation (LLM + TTS + STT) ─────────────────────────────────────

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface VoiceChatResponse {
  reply: string;
  history: ChatMessage[];
}

export async function voiceChat(
  convId: string,
  businessId: string,
  message: string,
  history: ChatMessage[],
  firstTurn = false
): Promise<VoiceChatResponse> {
  const res = await fetch(`${SERVICES.audio}/audio/voice/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conv_id: convId,
      business_id: businessId,
      message,
      history,
      first_turn: firstTurn,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Voice chat failed");
  }
  return res.json();
}

export async function voiceTTS(text: string, voice = "alloy"): Promise<Blob> {
  const res = await fetch(`${SERVICES.audio}/audio/voice/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice }),
  });
  if (!res.ok) throw new Error(`TTS failed: ${res.status}`);
  return res.blob();
}

export async function voiceSTT(audioBlob: Blob): Promise<{ text: string }> {
  const form = new FormData();
  form.append("file", audioBlob, "recording.webm");
  const res = await fetch(`${SERVICES.audio}/audio/voice/stt`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "STT failed");
  }
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface AuthResponse {
  access_token: string;
  token_type: string;
  business_id: string;
  username: string;
  business_name: string;
}

export interface MeResponse {
  id: string;
  username: string;
  email: string;
  business_id: string;
  created_at: string;
}

async function authPost(path: string, body: Record<string, string>): Promise<AuthResponse> {
  const res = await fetch(`${SERVICES.audio}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Auth request failed");
  }
  return res.json();
}

export function register(username: string, email: string, password: string, businessName = ""): Promise<AuthResponse> {
  return authPost("/auth/register", { username, email, password, business_name: businessName });
}

export function login(username: string, password: string): Promise<AuthResponse> {
  return authPost("/auth/login", { username, password });
}

export async function getMe(token: string): Promise<MeResponse> {
  const res = await fetch(`${SERVICES.audio}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Unauthorized");
  return res.json();
}

// ── Business Context ──────────────────────────────────────────────────────────

export interface BusinessContextItem {
  id: string;
  label: string;
  content: string;
  type: "manual" | "file";
  file_name?: string;
  created_at: string;
  updated_at: string;
}

function authHeaders(token: string): Record<string, string> {
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

export async function getContextItems(token: string): Promise<BusinessContextItem[]> {
  const res = await fetch(`${SERVICES.audio}/context`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to load context items");
  return res.json();
}

export async function createContextItem(
  token: string,
  label: string,
  content: string,
  type: "manual" | "file",
  refineWithAi = false,
  fileName?: string
): Promise<BusinessContextItem> {
  const res = await fetch(`${SERVICES.audio}/context`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ label, content, type, file_name: fileName, refine_with_ai: refineWithAi }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Create failed");
  }
  return res.json();
}

export async function updateContextItem(
  token: string,
  id: string,
  updates: { label?: string; content?: string },
  refineWithAi = false
): Promise<BusinessContextItem> {
  const res = await fetch(`${SERVICES.audio}/context/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify({ ...updates, refine_with_ai: refineWithAi }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Update failed");
  }
  return res.json();
}

export async function deleteContextItem(token: string, id: string): Promise<void> {
  const res = await fetch(`${SERVICES.audio}/context/${encodeURIComponent(id)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Delete failed");
  }
}

// ── Intelligence Engine ───────────────────────────────────────────────────────

export async function intelligenceStep(
  businessId: string,
  convId: string,
  segment: TranscriptSegment,
  sessionState?: Record<string, unknown>
): Promise<IntelligenceAction> {
  const res = await fetch(`${SERVICES.intelligence}/intelligence/step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      business_id: businessId,
      conv_id: convId,
      segment,
      session_state: sessionState ?? {},
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Intelligence step failed");
  }
  return res.json();
}
