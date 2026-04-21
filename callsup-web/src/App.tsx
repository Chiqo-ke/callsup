import { useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertCircle,
  Bot,
  Building2,
  CheckCircle2,
  FileText,
  KeyRound,
  LayoutDashboard,
  Loader2,
  LogIn,
  LogOut,
  MessageSquare,
  Mic,
  MicOff,
  Pencil,
  Phone,
  PhoneOff,
  RefreshCw,
  Server,
  ShieldCheck,
  Sparkles,
  Trash2,
  User,
  WifiOff,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Spinner } from "./components/ui/spinner";
import {
  fetchHealth,
  fetchTranscript,
  intelligenceStep,
  simulateCall,
  login,
  register,
  getContextItems,
  createContextItem,
  updateContextItem,
  deleteContextItem,
  voiceChat,
  voiceSTT,
  type BusinessContextItem,
  type ChatMessage,
  type HealthResult,
  type IntelligenceAction,
  type ServiceName,
  type TranscriptSegment,
} from "./lib/api";

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

type Page = "dashboard" | "transcripts" | "intelligence" | "context" | "simulation";

interface AuthState {
  token: string;
  businessId: string;
  username: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// Escalated ticket types & local store
// ──────────────────────────────────────────────────────────────────────────────

interface EscalatedTicket {
  id: string;
  conv_id: string;
  business_id: string;
  reason: string;
  timestamp: string;
  status: "pending" | "resolved";
}

function loadTickets(): EscalatedTicket[] {
  try {
    const raw = localStorage.getItem("callsup_tickets");
    return raw ? (JSON.parse(raw) as EscalatedTicket[]) : [];
  } catch {
    return [];
  }
}

function saveTickets(tickets: EscalatedTicket[]): void {
  localStorage.setItem("callsup_tickets", JSON.stringify(tickets));
}

// ──────────────────────────────────────────────────────────────────────────────
// Health hook — polls every 15 s
// ──────────────────────────────────────────────────────────────────────────────

function useServiceHealth() {
  const [health, setHealth] = useState<Record<ServiceName, HealthResult>>({
    audio: { service: "audio", status: "loading" },
    intelligence: { service: "intelligence", status: "loading" },
    llm: { service: "llm", status: "loading" },
  });

  const poll = async () => {
    const results = await Promise.all([
      fetchHealth("audio"),
      fetchHealth("intelligence"),
      fetchHealth("llm"),
    ]);
    const next: Record<ServiceName, HealthResult> = {} as never;
    for (const r of results) next[r.service] = r;
    setHealth(next);
  };

  useEffect(() => {
    poll();
    const id = setInterval(poll, 15_000);
    return () => clearInterval(id);
  }, []);

  return { health, refresh: poll };
}

// ──────────────────────────────────────────────────────────────────────────────
// Small helpers
// ──────────────────────────────────────────────────────────────────────────────

function ServiceDot({ status }: { status: HealthResult["status"] }) {
  if (status === "online")
    return <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />;
  if (status === "offline")
    return <span className="inline-block w-2 h-2 rounded-full bg-red-500" />;
  return <span className="inline-block w-2 h-2 rounded-full bg-slate-300 animate-pulse" />;
}

function serviceLabel(s: ServiceName) {
  return { audio: "Audio Engine", intelligence: "Intelligence", llm: "LLM Adapter" }[s];
}

// ──────────────────────────────────────────────────────────────────────────────
// Login / Register page
// ──────────────────────────────────────────────────────────────────────────────

function LoginPage({ onAuth }: { onAuth: (auth: AuthState) => void }) {
  const [tab, setTab] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const inputClass =
    "w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setErrorMsg("");
    try {
      let resp;
      if (tab === "login") {
        resp = await login(username.trim(), password);
      } else {
        resp = await register(username.trim(), email.trim(), password);
      }
      const auth: AuthState = {
        token: resp.access_token,
        businessId: resp.business_id,
        username: resp.username,
      };
      localStorage.setItem("callsup_auth", JSON.stringify(auth));
      onAuth(auth);
    } catch (err: unknown) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Authentication failed");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <ShieldCheck size={32} className="text-blue-600" />
          <div>
            <div className="text-2xl font-bold text-slate-900 leading-tight">CallSupport</div>
            <div className="text-xs text-slate-400 leading-tight">Operations Platform</div>
          </div>
        </div>

        <Card>
          <CardHeader className="pb-3">
            {/* Tabs */}
            <div className="flex gap-1 bg-slate-100 rounded-lg p-1">
              <button
                onClick={() => { setTab("login"); setStatus("idle"); setErrorMsg(""); }}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  tab === "login"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-700"
                }`}
              >
                <LogIn size={13} /> Sign In
              </button>
              <button
                onClick={() => { setTab("register"); setStatus("idle"); setErrorMsg(""); }}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  tab === "register"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-700"
                }`}
              >
                <KeyRound size={13} /> Register
              </button>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Username</label>
                <input
                  required
                  minLength={3}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="your-username"
                  className={inputClass}
                  autoComplete="username"
                />
              </div>
              {tab === "register" && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Email <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    className={inputClass}
                    autoComplete="email"
                  />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                <input
                  required
                  type="password"
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className={inputClass}
                  autoComplete={tab === "login" ? "current-password" : "new-password"}
                />
              </div>

              {status === "error" && (
                <div className="flex items-center gap-2 text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm">
                  <AlertCircle size={14} className="shrink-0" /> {errorMsg}
                </div>
              )}

              <button
                type="submit"
                disabled={status === "loading"}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {status === "loading" ? (
                  <><Loader2 size={14} className="animate-spin" /> {tab === "login" ? "Signing in…" : "Creating account…"}</>
                ) : tab === "login" ? (
                  <><LogIn size={14} /> Sign In</>
                ) : (
                  <><KeyRound size={14} /> Create Account</>
                )}
              </button>

              {tab === "register" && (
                <p className="text-xs text-slate-400 text-center">
                  A unique Business ID will be created automatically for your account.
                </p>
              )}
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Dashboard page
// ──────────────────────────────────────────────────────────────────────────────

function DashboardPage({
  health,
  refresh,
  tickets,
  onResolveTicket,
}: {
  health: Record<ServiceName, HealthResult>;
  refresh: () => void;
  tickets: EscalatedTicket[];
  onResolveTicket: (id: string) => void;
}) {
  const services: ServiceName[] = ["audio", "intelligence", "llm"];
  const online = services.filter((s) => health[s].status === "online").length;
  const pendingTickets = tickets.filter((t) => t.status === "pending");
  const resolvedToday = tickets.filter(
    (t) =>
      t.status === "resolved" &&
      new Date(t.timestamp).toDateString() === new Date().toDateString()
  ).length;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">Call support operations overview</p>
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800 border border-slate-200 rounded-lg px-3 py-1.5 hover:bg-slate-50 transition-colors"
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Stats row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="text-3xl font-bold text-amber-600">{pendingTickets.length}</div>
            <div className="text-sm text-slate-500 mt-1 flex items-center gap-1.5">
              <AlertCircle size={13} /> Tickets Pending
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="text-3xl font-bold text-emerald-600">{resolvedToday}</div>
            <div className="text-sm text-slate-500 mt-1 flex items-center gap-1.5">
              <CheckCircle2 size={13} /> Resolved Today
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="text-3xl font-bold text-slate-900">{tickets.length}</div>
            <div className="text-sm text-slate-500 mt-1 flex items-center gap-1.5">
              <Activity size={13} /> Total Escalations
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <div
              className={`text-3xl font-bold ${
                online === 3
                  ? "text-emerald-600"
                  : online === 0
                  ? "text-red-600"
                  : "text-amber-600"
              }`}
            >
              {online}/3
            </div>
            <div className="text-sm text-slate-500 mt-1 flex items-center gap-1.5">
              <Server size={13} /> Services Online
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Service health cards */}
      <div className="grid gap-4 md:grid-cols-3 mb-6">
        {services.map((svc) => {
          const h = health[svc];
          return (
            <Card key={svc}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-semibold">{serviceLabel(svc)}</CardTitle>
                  <Badge
                    variant={
                      h.status === "online"
                        ? "online"
                        : h.status === "offline"
                        ? "offline"
                        : "loading"
                    }
                  >
                    <ServiceDot status={h.status} />
                    {h.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                {h.version && <span className="text-xs text-slate-400">v{h.version}</span>}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Task Queue */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Phone size={15} className="text-slate-500" /> Task Queue
              </CardTitle>
              <CardDescription>Conversations escalated for human review</CardDescription>
            </div>
            {pendingTickets.length > 0 && (
              <Badge variant="warning">{pendingTickets.length} pending</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {tickets.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-slate-300 gap-2">
              <CheckCircle2 size={28} className="text-slate-200" />
              <p className="text-sm">No escalations yet — the queue is clear.</p>
              <p className="text-xs text-slate-300 mt-1">
                Tickets appear here when the AI engine flags a conversation for human review.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-400 border-b border-slate-100">
                    <th className="pb-2 font-medium pr-4">Conversation</th>
                    <th className="pb-2 font-medium pr-4">Reason</th>
                    <th className="pb-2 font-medium pr-4">Time</th>
                    <th className="pb-2 font-medium pr-4">Status</th>
                    <th className="pb-2 font-medium"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {tickets.map((ticket) => (
                    <tr key={ticket.id} className="text-slate-600">
                      <td className="py-3 pr-4 font-mono text-xs text-slate-700">
                        {ticket.conv_id}
                      </td>
                      <td className="py-3 pr-4 text-xs max-w-xs">
                        <span className="line-clamp-2">{ticket.reason}</span>
                      </td>
                      <td className="py-3 pr-4 text-xs text-slate-400 whitespace-nowrap">
                        {new Date(ticket.timestamp).toLocaleString()}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant={ticket.status === "pending" ? "warning" : "online"}>
                          {ticket.status}
                        </Badge>
                      </td>
                      <td className="py-3">
                        {ticket.status === "pending" && (
                          <button
                            onClick={() => onResolveTicket(ticket.id)}
                            className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                          >
                            Resolve
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Transcripts page
// ──────────────────────────────────────────────────────────────────────────────

function TranscriptsPage() {
  const [convId, setConvId] = useState("");
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleFetch = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setErrorMsg("");
    setSegments([]);
    try {
      const data = await fetchTranscript(convId.trim());
      setSegments(data);
      setStatus("ok");
    } catch (err: unknown) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Unknown error");
    }
  };

  const formatMs = (ms: number) => {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    return `${m}:${String(s % 60).padStart(2, "0")}`;
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-1">Transcripts</h1>
      <p className="text-sm text-slate-500 mb-6">
        Retrieve PII-redacted transcript segments for any conversation.
      </p>

      <Card className="max-w-lg mb-6">
        <CardContent className="pt-6">
          <form onSubmit={handleFetch} className="flex gap-2">
            <input
              required
              value={convId}
              onChange={(e) => setConvId(e.target.value)}
              placeholder="Conversation ID"
              className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={status === "loading"}
              className="flex items-center gap-1.5 bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {status === "loading" ? <Spinner className="text-white" /> : <FileText size={15} />}
              Fetch
            </button>
          </form>
        </CardContent>
      </Card>

      {status === "error" && (
        <div className="flex items-center gap-2 text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm mb-4 max-w-lg">
          <AlertCircle size={15} className="shrink-0" /> {errorMsg}
        </div>
      )}

      {status === "ok" && segments.length === 0 && (
        <p className="text-sm text-slate-400">No segments found for this conversation.</p>
      )}

      {segments.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              {segments.length} segment{segments.length !== 1 ? "s" : ""} — conv: {convId}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {segments.map((seg, i) => (
                <div
                  key={i}
                  className="flex gap-3 p-3 bg-slate-50 rounded-lg border border-slate-100"
                >
                  <div className="shrink-0 text-xs text-slate-400 pt-0.5 w-20">
                    <div className="font-semibold text-slate-600">{seg.speaker}</div>
                    <div>{formatMs(seg.start_ms)} → {formatMs(seg.end_ms)}</div>
                    {seg.confidence !== undefined && (
                      <div className="mt-0.5">
                        <Badge
                          variant={seg.confidence >= 0.8 ? "online" : "warning"}
                        >
                          {(seg.confidence * 100).toFixed(0)}%
                        </Badge>
                      </div>
                    )}
                  </div>
                  <div className="text-sm text-slate-800 leading-relaxed">{seg.text}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Intelligence page
// ──────────────────────────────────────────────────────────────────────────────

function IntelligencePage({
  businessId,
  onEscalate,
}: {
  businessId: string;
  onEscalate: (ticket: EscalatedTicket) => void;
}) {
  const [convId, setConvId] = useState("");
  const [speaker, setSpeaker] = useState("agent");
  const [text, setText] = useState("");
  const [startMs, setStartMs] = useState("0");
  const [endMs, setEndMs] = useState("3000");
  const [result, setResult] = useState<IntelligenceAction | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setResult(null);
    setErrorMsg("");
    const segment = {
      speaker,
      text,
      start_ms: Number(startMs),
      end_ms: Number(endMs),
    };
    try {
      const action = await intelligenceStep(businessId.trim(), convId.trim(), segment);
      setResult(action);
      setStatus("ok");
      if (action.escalate) {
        onEscalate({
          id: `${convId.trim()}-${Date.now()}`,
          conv_id: convId.trim(),
          business_id: businessId.trim(),
          reason: action.response_text,
          timestamp: new Date().toISOString(),
          status: "pending",
        });
      }
    } catch (err: unknown) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Unknown error");
    }
  };

  const inputClass =
    "w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-1">Intelligence Step</h1>
      <p className="text-sm text-slate-500 mb-6">
        Send a transcript segment to the Intelligence Engine and see the recommended action.
      </p>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-1">Conversation ID</label>
                  <input required value={convId} onChange={(e) => setConvId(e.target.value)} placeholder="conv-1025" className={inputClass} />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Speaker</label>
                  <input required value={speaker} onChange={(e) => setSpeaker(e.target.value)} placeholder="agent" className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Start ms</label>
                  <input required type="number" min={0} value={startMs} onChange={(e) => setStartMs(e.target.value)} className={inputClass} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">End ms</label>
                  <input required type="number" min={0} value={endMs} onChange={(e) => setEndMs(e.target.value)} className={inputClass} />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Transcript Text</label>
                <textarea
                  required
                  rows={4}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="What the speaker said…"
                  className={inputClass}
                />
              </div>

              {status === "error" && (
                <div className="flex items-center gap-2 text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm">
                  <AlertCircle size={15} className="shrink-0" /> {errorMsg}
                </div>
              )}

              <button
                type="submit"
                disabled={status === "loading"}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {status === "loading" ? (
                  <><Spinner className="text-white" /> Analysing…</>
                ) : (
                  <><Zap size={15} /> Run Intelligence Step</>
                )}
              </button>
            </form>
          </CardContent>
        </Card>

        {/* Result panel */}
        <div>
          {status === "idle" && (
            <div className="h-full flex items-center justify-center text-slate-300 text-sm flex-col gap-3 border-2 border-dashed border-slate-100 rounded-xl p-8">
              <Zap size={32} className="text-slate-200" />
              Submit a segment to see the recommended action.
            </div>
          )}
          {status === "loading" && (
            <div className="h-full flex items-center justify-center text-slate-400 gap-2">
              <Loader2 size={20} className="animate-spin" /> Processing…
            </div>
          )}
          {status === "ok" && result && (
            <Card className="h-full border-blue-100">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <CheckCircle2 size={16} className="text-emerald-500" />
                  Action Recommended
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 w-28 shrink-0">Action type</span>
                  <Badge variant="default">{result.action_type}</Badge>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-xs text-slate-400 w-28 shrink-0">Response</span>
                  <p className="text-sm text-slate-800 leading-relaxed">{result.response_text}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 w-28 shrink-0">TTS</span>
                  <Badge variant={result.tts ? "online" : "default"}>{result.tts ? "Yes" : "No"}</Badge>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 w-28 shrink-0">Escalate</span>
                  <Badge variant={result.escalate ? "warning" : "online"}>
                    {result.escalate ? "Escalate" : "No escalation"}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Business Context Manager page
// ──────────────────────────────────────────────────────────────────────────────

function BusinessContextPage({ token }: { token: string }) {
  const [items, setItems] = useState<BusinessContextItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<"text" | "file">("text");
  const [label, setLabel] = useState("");
  const [content, setContent] = useState("");
  const [fileInfo, setFileInfo] = useState<{ name: string; content: string } | null>(null);
  const [refineWithAi, setRefineWithAi] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState("");
  const [editContent, setEditContent] = useState("");
  const [editRefine, setEditRefine] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);
  const [apiError, setApiError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const loadItems = async () => {
    try {
      const data = await getContextItems(token);
      setItems(data);
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Failed to load context");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadItems(); }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      setFileInfo({ name: file.name, content: text });
      if (!label) setLabel(file.name.replace(/\.[^/.]+$/, ""));
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const handleAdd = async () => {
    const text = mode === "file" ? fileInfo?.content ?? "" : content;
    if (!label.trim() || !text.trim()) return;
    setSaving(true);
    setApiError("");
    try {
      const item = await createContextItem(
        token,
        label.trim(),
        text,
        mode === "file" ? "file" : "manual",
        refineWithAi,
        mode === "file" ? fileInfo?.name : undefined,
      );
      setItems((prev) => [...prev, item]);
      setLabel("");
      setContent("");
      setFileInfo(null);
      setRefineWithAi(false);
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Failed to save context");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    setApiError("");
    try {
      await deleteContextItem(token, id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  const startEdit = (item: BusinessContextItem) => {
    setEditingId(item.id);
    setEditLabel(item.label);
    setEditContent(item.content);
    setEditRefine(false);
  };

  const handleSaveEdit = async (id: string) => {
    setSavingEdit(true);
    setApiError("");
    try {
      const updated = await updateContextItem(token, id, { label: editLabel, content: editContent }, editRefine);
      setItems((prev) => prev.map((i) => (i.id === id ? updated : i)));
      setEditingId(null);
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Failed to update");
    } finally {
      setSavingEdit(false);
    }
  };

  const inputClass =
    "w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-1">Business Context Manager</h1>
      <p className="text-sm text-slate-500 mb-6">
        Add business details so the Call Support Engine has context during calls. Your context is
        stored securely on the server and tied to your account.
      </p>

      {apiError && (
        <div className="flex items-center gap-2 text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm mb-4">
          <AlertCircle size={14} className="shrink-0" /> {apiError}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {/* Add context panel */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Add Context</CardTitle>
            <CardDescription>
              Describe your business, products, FAQs, escalation policies, etc.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Mode tabs */}
            <div className="flex gap-1 bg-slate-100 rounded-lg p-1 w-fit">
              <button
                onClick={() => setMode("text")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  mode === "text"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-700"
                }`}
              >
                <MessageSquare size={13} /> Type manually
              </button>
              <button
                onClick={() => setMode("file")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  mode === "file"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-700"
                }`}
              >
                <Upload size={13} /> Upload file
              </button>
            </div>

            {/* Label */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Label / Title</label>
              <input
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="e.g. Company Overview"
                className={inputClass}
              />
            </div>

            {mode === "text" ? (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Content</label>
                <textarea
                  rows={6}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Paste or type business context here…"
                  className={`${inputClass} resize-y`}
                />
              </div>
            ) : (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  File (.txt, .md, .csv)
                </label>
                <div
                  onClick={() => fileRef.current?.click()}
                  className="border-2 border-dashed border-slate-200 rounded-lg p-5 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
                >
                  <Upload size={18} className="mx-auto text-slate-400 mb-1" />
                  {fileInfo ? (
                    <>
                      <p className="text-sm font-medium text-slate-700">{fileInfo.name}</p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {fileInfo.content.length.toLocaleString()} characters
                      </p>
                    </>
                  ) : (
                    <p className="text-sm text-slate-400">Click to choose a text file</p>
                  )}
                </div>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".txt,.md,.csv,.json"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>
            )}

            {/* Refine with AI toggle */}
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={refineWithAi}
                onChange={(e) => setRefineWithAi(e.target.checked)}
                className="rounded"
              />
              <span className="flex items-center gap-1.5 text-sm text-slate-700">
                <Sparkles size={13} className="text-blue-500" /> Refine with AI
              </span>
            </label>

            <button
              onClick={handleAdd}
              disabled={saving || !label.trim() || (mode === "text" ? !content.trim() : !fileInfo)}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <CheckCircle2 size={14} />
              )}
              {saving ? (refineWithAi ? "Refining with AI…" : "Saving…") : "Save Context"}
            </button>
          </CardContent>
        </Card>

        {/* Saved context panel */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-700">
              Saved Context ({loading ? "…" : items.length})
            </h2>
            {items.length > 0 && (
              <span className="text-xs text-slate-400">Passed to intelligence engine on each call</span>
            )}
          </div>

          {loading ? (
            <div className="flex items-center justify-center border-2 border-dashed border-slate-100 rounded-xl p-10">
              <Loader2 size={20} className="animate-spin text-slate-300" />
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center border-2 border-dashed border-slate-100 rounded-xl p-10 text-center text-slate-300">
              <Building2 size={28} className="mb-2 text-slate-200" />
              <p className="text-sm">No context saved yet.</p>
              <p className="text-xs mt-1">Add business details on the left.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <Card key={item.id} className="border border-slate-100">
                  <CardContent className="pt-4 pb-3">
                    {editingId === item.id ? (
                      <div className="space-y-2">
                        <input
                          value={editLabel}
                          onChange={(e) => setEditLabel(e.target.value)}
                          className={inputClass}
                          placeholder="Label"
                        />
                        <textarea
                          rows={4}
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          className={`${inputClass} resize-y`}
                        />
                        <label className="flex items-center gap-2 cursor-pointer select-none text-sm text-slate-700">
                          <input
                            type="checkbox"
                            checked={editRefine}
                            onChange={(e) => setEditRefine(e.target.checked)}
                            className="rounded"
                          />
                          <Sparkles size={12} className="text-blue-500" /> Refine with AI
                        </label>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleSaveEdit(item.id)}
                            disabled={savingEdit}
                            className="flex items-center gap-1.5 bg-blue-600 text-white rounded-lg px-3 py-1.5 text-xs font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                          >
                            {savingEdit ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
                            {savingEdit ? (editRefine ? "Refining…" : "Saving…") : "Save"}
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="flex items-center gap-1.5 border border-slate-200 text-slate-600 rounded-lg px-3 py-1.5 text-xs hover:bg-slate-50 transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            {item.type === "file" ? (
                              <FileText size={14} className="text-blue-400 shrink-0" />
                            ) : (
                              <MessageSquare size={14} className="text-slate-400 shrink-0" />
                            )}
                            <span className="text-sm font-medium text-slate-800 truncate">
                              {item.label}
                            </span>
                            {item.file_name && (
                              <span className="text-xs text-slate-400 truncate hidden sm:block">
                                ({item.file_name})
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-1 shrink-0">
                            <button
                              onClick={() => startEdit(item)}
                              className="text-slate-300 hover:text-blue-500 transition-colors"
                              title="Edit"
                            >
                              <Pencil size={14} />
                            </button>
                            <button
                              onClick={() => handleDelete(item.id)}
                              className="text-slate-300 hover:text-red-500 transition-colors"
                              title="Delete"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                        <p className="mt-2 text-xs text-slate-400 leading-relaxed line-clamp-3">
                          {item.content}
                        </p>
                        <p className="mt-1.5 text-xs text-slate-300">
                          {new Date(item.created_at).toLocaleString()}
                        </p>
                      </>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Call Simulation Chat page
// ──────────────────────────────────────────────────────────────────────────────

interface ChatBubble {
  speaker: string;
  text: string;
  isAgent: boolean;
  confidence?: number;
  intelligenceAction?: IntelligenceAction;
}

function CallSimulationPage({
  businessId,
  token: _token,
  onEscalate: _onEscalate,
}: {
  businessId: string;
  token: string;
  onEscalate: (ticket: EscalatedTicket) => void;
}) {
  type CallStatus = "idle" | "connecting" | "active" | "listening" | "processing" | "speaking" | "ended" | "error";

  const [callStatus, setCallStatus] = useState<CallStatus>("idle");
  const [convId, setConvId] = useState("");
  const [businessIdInput, setBusinessIdInput] = useState(businessId || "demo-business");
  const [bubbles, setBubbles] = useState<ChatBubble[]>([]);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [errorMsg, setErrorMsg] = useState("");
  const [statusLabel, setStatusLabel] = useState("Ready — press Answer Call to begin");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest bubble
  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [bubbles]);

  const playTTS = (text: string): Promise<void> => {
    setCallStatus("speaking");
    setStatusLabel("Agent is speaking…");
    return new Promise<void>((resolve) => {
      window.speechSynthesis.cancel();
      const utt = new SpeechSynthesisUtterance(text);
      utt.lang = "en-US";
      utt.rate = 1.0;
      utt.onend = () => {
        setCallStatus("active");
        setStatusLabel("Hold the mic button to speak");
        resolve();
      };
      utt.onerror = () => {
        setCallStatus("active");
        setStatusLabel("Hold the mic button to speak");
        resolve();
      };
      window.speechSynthesis.speak(utt);
    });
  };

  const handleAnswerCall = async () => {
    setCallStatus("connecting");
    setErrorMsg("");
    setBubbles([]);
    setHistory([]);
    const cid = `call-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setConvId(cid);
    setStatusLabel("Requesting microphone access…");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      setStatusLabel("Connecting to AI agent…");
      const resp = await voiceChat(cid, businessIdInput, "", [], true);
      setHistory(resp.history);
      setBubbles([{ speaker: "Agent", text: resp.reply, isAgent: true }]);
      await playTTS(resp.reply);
    } catch (err) {
      setCallStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Failed to start call");
      setStatusLabel("Error — see below");
    }
  };

  const startRecording = () => {
    if (!streamRef.current || callStatus !== "active") return;
    audioChunksRef.current = [];
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : MediaRecorder.isTypeSupported("audio/webm")
      ? "audio/webm"
      : "audio/ogg";
    const recorder = new MediaRecorder(streamRef.current, { mimeType });
    recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
    recorder.start(250);
    mediaRecorderRef.current = recorder;
    setCallStatus("listening");
    setStatusLabel("Listening… release to send");
  };

  const stopRecording = async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    await new Promise<void>((resolve) => { recorder.onstop = () => resolve(); recorder.stop(); });
    setCallStatus("processing");
    setStatusLabel("Transcribing speech…");
    const mimeType = audioChunksRef.current[0]?.type || "audio/webm";
    const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
    if (audioBlob.size < 100) {
      setCallStatus("active");
      setStatusLabel("No audio captured — hold longer to speak");
      return;
    }
    try {
      const sttResult = await voiceSTT(audioBlob);
      const userText = sttResult.text.trim();
      if (!userText) {
        setCallStatus("active");
        setStatusLabel("Nothing detected — hold to speak again");
        return;
      }
      setBubbles((prev) => [...prev, { speaker: "You", text: userText, isAgent: false }]);
      setStatusLabel("Agent is thinking…");
      const chatResp = await voiceChat(convId, businessIdInput, userText, history, false);
      setHistory(chatResp.history);
      setBubbles((prev) => [...prev, { speaker: "Agent", text: chatResp.reply, isAgent: true }]);
      await playTTS(chatResp.reply);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Error processing speech");
      setCallStatus("active");
      setStatusLabel("Error — try again");
    }
  };

  const handleEndCall = () => {
    if (currentAudioRef.current) { currentAudioRef.current.pause(); currentAudioRef.current = null; }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") mediaRecorderRef.current.stop();
    if (streamRef.current) { streamRef.current.getTracks().forEach((t) => t.stop()); streamRef.current = null; }
    setCallStatus("ended");
    setStatusLabel("Call ended");
  };

  const handleReset = () => {
    handleEndCall();
    setCallStatus("idle");
    setBubbles([]);
    setHistory([]);
    setConvId("");
    setErrorMsg("");
    setStatusLabel("Ready — press Answer Call to begin");
  };

  const isLive = callStatus !== "idle" && callStatus !== "ended" && callStatus !== "error";
  const canRecord = callStatus === "active";
  const isListening = callStatus === "listening";
  const isConnecting = callStatus === "connecting";

  const statusColor: Record<CallStatus, string> = {
    idle: "bg-slate-300",
    connecting: "bg-amber-400 animate-pulse",
    active: "bg-emerald-400",
    listening: "bg-red-500 animate-pulse",
    processing: "bg-blue-400 animate-pulse",
    speaking: "bg-blue-600 animate-pulse",
    ended: "bg-slate-400",
    error: "bg-red-600",
  };

  return (
    <div className="flex flex-col h-full">
      <h1 className="text-2xl font-bold text-slate-900 mb-1">Live Call Simulation</h1>
      <p className="text-sm text-slate-500 mb-6">
        Answer the call, speak with the AI agent using your microphone, and hear responses in real time.
      </p>

      <div className="grid gap-6 lg:grid-cols-[340px_1fr] flex-1 min-h-0">
        {/* Config / control panel */}
        <div className="flex flex-col gap-4 self-start">
          <Card>
            <CardContent className="pt-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Business</label>
                <input
                  type="text"
                  value={businessIdInput}
                  onChange={(e) => setBusinessIdInput(e.target.value)}
                  disabled={isLive}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-400"
                  placeholder="e.g. demo-business"
                />
              </div>

              {convId && (
                <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 text-xs text-emerald-700">
                  <Phone size={12} className="shrink-0" />
                  <span>Call ID: <span className="font-mono font-semibold">{convId}</span></span>
                </div>
              )}

              {errorMsg && (
                <div className="flex items-center gap-2 text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm">
                  <AlertCircle size={15} className="shrink-0" /> {errorMsg}
                </div>
              )}

              {/* Action buttons */}
              <div className="flex flex-col gap-2">
                {!isLive && callStatus !== "ended" && (
                  <button
                    onClick={handleAnswerCall}
                    className="flex items-center justify-center gap-2 bg-emerald-600 text-white rounded-lg px-4 py-2.5 text-sm font-medium hover:bg-emerald-700 transition-colors"
                  >
                    {isConnecting ? (
                      <><Loader2 size={15} className="animate-spin" /> Connecting…</>
                    ) : (
                      <><Phone size={15} /> Answer Call</>
                    )}
                  </button>
                )}

                {isLive && (
                  <button
                    onClick={handleEndCall}
                    className="flex items-center justify-center gap-2 bg-red-600 text-white rounded-lg px-4 py-2.5 text-sm font-medium hover:bg-red-700 transition-colors"
                  >
                    <PhoneOff size={15} /> End Call
                  </button>
                )}

                {(callStatus === "ended" || callStatus === "error") && (
                  <button
                    onClick={handleReset}
                    className="flex items-center justify-center gap-2 border border-slate-200 text-slate-600 rounded-lg px-4 py-2.5 text-sm hover:bg-slate-50 transition-colors"
                  >
                    <RefreshCw size={14} /> New Call
                  </button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Push-to-talk button */}
          {isLive && (
            <Card>
              <CardContent className="pt-5 flex flex-col items-center gap-3">
                <p className="text-xs text-slate-500 text-center">Hold to speak, release to send</p>
                <button
                  onMouseDown={startRecording}
                  onMouseUp={stopRecording}
                  onTouchStart={(e) => { e.preventDefault(); startRecording(); }}
                  onTouchEnd={(e) => { e.preventDefault(); stopRecording(); }}
                  disabled={!canRecord && !isListening}
                  className={`w-20 h-20 rounded-full flex items-center justify-center transition-all shadow-md
                    ${isListening
                      ? "bg-red-500 scale-110 shadow-red-200"
                      : canRecord
                      ? "bg-blue-600 hover:bg-blue-700 hover:scale-105"
                      : "bg-slate-200 cursor-not-allowed"
                    }`}
                >
                  {isListening ? (
                    <MicOff size={28} className="text-white" />
                  ) : (
                    <Mic size={28} className={canRecord ? "text-white" : "text-slate-400"} />
                  )}
                </button>
                <p className={`text-xs font-medium ${isListening ? "text-red-500" : "text-slate-400"}`}>
                  {isListening ? "Recording…" : canRecord ? "Ready" : statusLabel}
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Chat view */}
        <div className="flex flex-col min-h-0">
          {/* Call header */}
          <div className="flex items-center gap-3 bg-white border border-slate-200 rounded-t-xl px-4 py-3 shrink-0">
            <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${statusColor[callStatus]}`} />
            <span className="text-sm font-medium text-slate-800">
              {convId ? `${businessIdInput} — ${convId}` : "No active call"}
            </span>
            <span className="text-xs text-slate-400 ml-auto">{statusLabel}</span>
          </div>

          {/* Messages */}
          <div
            ref={chatRef}
            className="flex-1 overflow-y-auto bg-slate-50 border-x border-slate-200 p-4 space-y-3 min-h-100 max-h-150"
          >
            {bubbles.length === 0 && callStatus === "idle" && (
              <div className="flex flex-col items-center justify-center h-full text-slate-300 gap-3 pt-16">
                <Phone size={36} className="text-slate-200" />
                <p className="text-sm">Press Answer Call to start a live conversation with the AI agent.</p>
              </div>
            )}

            {bubbles.length === 0 && isConnecting && (
              <div className="flex items-center justify-center h-full gap-2 text-slate-400 pt-16">
                <Loader2 size={18} className="animate-spin" />
                <span className="text-sm">{statusLabel}</span>
              </div>
            )}

            {bubbles.map((bubble, i) => (
              <div
                key={i}
                className={`flex items-end gap-2 ${bubble.isAgent ? "flex-row-reverse" : "flex-row"}`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                    bubble.isAgent ? "bg-blue-600" : "bg-slate-400"
                  }`}
                >
                  {bubble.isAgent ? (
                    <Bot size={15} className="text-white" />
                  ) : (
                    <User size={15} className="text-white" />
                  )}
                </div>

                <div className={`flex flex-col gap-1 max-w-[70%] ${bubble.isAgent ? "items-end" : "items-start"}`}>
                  <span className="text-xs text-slate-400 px-1">{bubble.speaker}</span>
                  <div
                    className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                      bubble.isAgent
                        ? "bg-blue-600 text-white rounded-br-sm"
                        : "bg-white text-slate-800 border border-slate-200 rounded-bl-sm"
                    }`}
                  >
                    {bubble.text}
                  </div>
                </div>
              </div>
            ))}

            {/* Typing indicator while agent is thinking/speaking */}
            {(callStatus === "processing" || callStatus === "speaking") && bubbles.length > 0 && (
              <div className="flex items-end gap-2 flex-row-reverse">
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                  <Bot size={15} className="text-white" />
                </div>
                <div className="bg-blue-50 border border-blue-100 rounded-2xl rounded-br-sm px-4 py-3">
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:0ms]" />
                    <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:150ms]" />
                    <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:300ms]" />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="bg-white border border-t-0 border-slate-200 rounded-b-xl px-4 py-3 shrink-0">
            <p className="text-xs text-slate-400">
              {callStatus === "ended"
                ? `Call ended — ${bubbles.length} messages exchanged`
                : callStatus === "idle"
                ? "Powered by OpenAI GPT-4o · Whisper STT · TTS"
                : statusLabel}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Root
// ──────────────────────────────────────────────────────────────────────────────

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const { health, refresh } = useServiceHealth();
  const [tickets, setTickets] = useState<EscalatedTicket[]>(loadTickets);
  const [auth, setAuth] = useState<AuthState | null>(() => {
    try {
      const stored = localStorage.getItem("callsup_auth");
      return stored ? (JSON.parse(stored) as AuthState) : null;
    } catch {
      return null;
    }
  });

  const addTicket = (ticket: EscalatedTicket) => {
    setTickets((prev) => {
      const next = [...prev, ticket];
      saveTickets(next);
      return next;
    });
  };

  const resolveTicket = (id: string) => {
    setTickets((prev) => {
      const next = prev.map((t) => (t.id === id ? { ...t, status: "resolved" as const } : t));
      saveTickets(next);
      return next;
    });
  };

  const handleLogout = () => {
    localStorage.removeItem("callsup_auth");
    setAuth(null);
  };

  if (!auth) return <LoginPage onAuth={setAuth} />;

  const navItems: { id: Page; label: string; icon: React.ReactNode }[] = [
    { id: "dashboard", label: "Dashboard", icon: <LayoutDashboard size={16} /> },
    { id: "transcripts", label: "Transcripts", icon: <FileText size={16} /> },
    { id: "intelligence", label: "AI Demo", icon: <Zap size={16} /> },
    { id: "context", label: "Business Context", icon: <Building2 size={16} /> },
    { id: "simulation", label: "Call Simulation", icon: <MessageSquare size={16} /> },
  ];

  const onlineCount = Object.values(health).filter((h) => h.status === "online").length;

  return (
    <div className="flex min-h-screen bg-slate-50 font-sans">
      {/* Sidebar */}
      <aside className="w-60 bg-slate-900 text-slate-50 flex flex-col shrink-0">
        <div className="flex h-16 items-center px-5 border-b border-slate-800 gap-3">
          <ShieldCheck size={20} className="text-blue-400 shrink-0" />
          <div>
            <div className="font-bold text-sm leading-tight">CallSupport</div>
            <div className="text-xs text-slate-400 leading-tight">Operations Platform</div>
          </div>
        </div>

        {/* Health summary in sidebar */}
        <div className="px-5 py-3 border-b border-slate-800">
          <div className="flex items-center gap-2 text-xs">
            {onlineCount === 3 ? (
              <><CheckCircle2 size={12} className="text-emerald-400" /><span className="text-emerald-400">All services online</span></>
            ) : onlineCount === 0 ? (
              <><WifiOff size={12} className="text-red-400" /><span className="text-red-400">Services offline</span></>
            ) : (
              <><Activity size={12} className="text-amber-400" /><span className="text-amber-400">{onlineCount}/3 services online</span></>
            )}
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-0.5">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-left transition-colors ${
                page === item.id
                  ? "bg-blue-600 text-white font-medium"
                  : "text-slate-300 hover:bg-slate-800 hover:text-slate-50"
              }`}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>

        {/* Service status list at bottom */}
        <div className="p-3 border-t border-slate-800 space-y-1.5">
          {(["audio", "intelligence", "llm"] as ServiceName[]).map((svc) => (
            <div key={svc} className="flex items-center justify-between text-xs px-1">
              <span className="flex items-center gap-1.5 text-slate-400">
                <Server size={10} />
                {serviceLabel(svc)}
              </span>
              <span
                className={
                  health[svc].status === "online"
                    ? "text-emerald-400"
                    : health[svc].status === "offline"
                    ? "text-red-400"
                    : "text-slate-500"
                }
              >
                {health[svc].status === "loading" ? (
                  <Spinner className="w-2.5 h-2.5 text-slate-500" />
                ) : (
                  health[svc].status
                )}
              </span>
            </div>
          ))}
        </div>

        <div className="px-4 py-3 border-t border-slate-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <User size={13} className="text-slate-400 shrink-0" />
              <span className="text-xs text-slate-400 truncate">{auth.username}</span>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1 text-slate-500 hover:text-red-400 transition-colors"
              title="Sign out"
            >
              <LogOut size={13} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 p-8 overflow-auto min-w-0">
        {page === "dashboard" && <DashboardPage health={health} refresh={refresh} tickets={tickets} onResolveTicket={resolveTicket} />}
        {page === "transcripts" && <TranscriptsPage />}
        {page === "intelligence" && <IntelligencePage businessId={auth.businessId} onEscalate={addTicket} />}
        {page === "context" && <BusinessContextPage token={auth.token} />}
        {page === "simulation" && <CallSimulationPage businessId={auth.businessId} token={auth.token} onEscalate={addTicket} />}
      </main>
    </div>
  );
}

