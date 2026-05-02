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
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  User,
  WifiOff,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Spinner } from "./components/ui/spinner";
import {
  SERVICES,
  fetchHealth,
  fetchTranscript,
  intelligenceStep,
  login,
  register,
  getContextItems,
  createContextItem,
  updateContextItem,
  deleteContextItem,
  voiceChat,
  voiceSTT,
  listEscalationRules,
  createEscalationRule,
  updateEscalationRule,
  deleteEscalationRule,
  listEscalationQueue,
  updateEscalationTicket,
  getEscalationTicket,
  type BusinessContextItem,
  type ChatMessage,
  type EscalationRule,
  type EscalationTicket,
  type HealthResult,
  type IntelligenceAction,
  type ServiceName,
  type TranscriptSegment,
} from "./lib/api";

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

type Page = "dashboard" | "transcripts" | "intelligence" | "context" | "escalation-rules" | "simulation";

interface AuthState {
  token: string;
  businessId: string;
  username: string;
  businessName: string;
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

function LoginPage({ onAuth, onGoToRegister }: { onAuth: (auth: AuthState) => void; onGoToRegister: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const inputClass =
    "w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setErrorMsg("");
    try {
      const resp = await login(username.trim(), password);
      const auth: AuthState = {
        token: resp.access_token,
        businessId: resp.business_id,
        username: resp.username,
        businessName: resp.business_name || resp.username,
      };
      localStorage.setItem("callsup_auth", JSON.stringify(auth));
      onAuth(auth);
    } catch (err: unknown) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Invalid credentials");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-blue-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-10">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
            <ShieldCheck size={22} className="text-white" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white leading-tight">CallSupport</div>
            <div className="text-xs text-slate-400 leading-tight">AI Business Phone Platform</div>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <h1 className="text-xl font-bold text-slate-900 mb-1">Welcome back</h1>
          <p className="text-sm text-slate-500 mb-6">Sign in to your account to continue.</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Username</label>
              <input
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="your-username"
                className={inputClass}
                autoComplete="username"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Password</label>
              <input
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className={inputClass}
                autoComplete="current-password"
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
              className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-2.5 text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors mt-2"
            >
              {status === "loading" ? (
                <><Loader2 size={14} className="animate-spin" /> Signing in…</>
              ) : (
                <><LogIn size={14} /> Sign In</>
              )}
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-6">
            New to CallSupport?{" "}
            <button
              onClick={onGoToRegister}
              className="text-blue-600 font-semibold hover:underline"
            >
              Create your account →
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Multi-step Register page
// ──────────────────────────────────────────────────────────────────────────────

function RegisterPage({ onAuth, onBackToLogin }: { onAuth: (auth: AuthState) => void; onBackToLogin: () => void }) {
  const [step, setStep] = useState<1 | 2>(1);
  const [registeredAuth, setRegisteredAuth] = useState<AuthState | null>(null);

  // Step 1
  const [businessName, setBusinessName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  // Step 2
  const [contextItems, setContextItems] = useState<{ label: string; content: string }[]>([]);
  const [ctxLabel, setCtxLabel] = useState("");
  const [ctxContent, setCtxContent] = useState("");
  const [ctxSaving, setCtxSaving] = useState(false);
  const [ctxError, setCtxError] = useState("");

  const inputClass =
    "w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white";

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setStatus("error");
      setErrorMsg("Passwords do not match");
      return;
    }
    setStatus("loading");
    setErrorMsg("");
    try {
      const resp = await register(username.trim(), email.trim(), password, businessName.trim());
      const auth: AuthState = {
        token: resp.access_token,
        businessId: resp.business_id,
        username: resp.username,
        businessName: resp.business_name || resp.username,
      };
      localStorage.setItem("callsup_auth", JSON.stringify(auth));
      setRegisteredAuth(auth);
      setStep(2);
    } catch (err: unknown) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Registration failed");
    }
  };

  const handleAddContext = async () => {
    if (!ctxLabel.trim() || !ctxContent.trim() || !registeredAuth) return;
    setCtxSaving(true);
    setCtxError("");
    try {
      await createContextItem(registeredAuth.token, ctxLabel.trim(), ctxContent.trim(), "manual", false);
      setContextItems((prev) => [...prev, { label: ctxLabel.trim(), content: ctxContent.trim() }]);
      setCtxLabel("");
      setCtxContent("");
    } catch (err: unknown) {
      setCtxError(err instanceof Error ? err.message : "Failed to save context");
    } finally {
      setCtxSaving(false);
    }
  };

  const handleFinish = () => {
    if (registeredAuth) onAuth(registeredAuth);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-blue-950 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
            <ShieldCheck size={22} className="text-white" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white leading-tight">CallSupport</div>
            <div className="text-xs text-slate-400 leading-tight">AI Business Phone Platform</div>
          </div>
        </div>

        {/* Step indicators */}
        <div className="flex items-center justify-center gap-3 mb-6">
          <div className={`flex items-center gap-2 text-sm font-medium ${step === 1 ? "text-blue-400" : "text-emerald-400"}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${step > 1 ? "bg-emerald-500 text-white" : "bg-blue-600 text-white"}`}>
              {step > 1 ? <CheckCircle2 size={14} /> : "1"}
            </div>
            Account
          </div>
          <div className="w-12 h-px bg-slate-600" />
          <div className={`flex items-center gap-2 text-sm font-medium ${step === 2 ? "text-blue-400" : "text-slate-500"}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${step === 2 ? "bg-blue-600 text-white" : "bg-slate-700 text-slate-400"}`}>
              2
            </div>
            Business Setup
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {step === 1 ? (
            <>
              <h1 className="text-xl font-bold text-slate-900 mb-1">Create your account</h1>
              <p className="text-sm text-slate-500 mb-6">Get started with AI-powered call support for your business.</p>

              <form onSubmit={handleCreateAccount} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Business Name <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <input
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    placeholder="e.g. Acme Corp"
                    className={inputClass}
                    autoComplete="off"
                  />
                  <p className="text-xs text-slate-400 mt-1">Your AI agent will greet callers using this name.</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">
                      Username <span className="text-red-500">*</span>
                    </label>
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
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">
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
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Password <span className="text-red-500">*</span>
                  </label>
                  <input
                    required
                    type="password"
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    className={inputClass}
                    autoComplete="new-password"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Confirm Password <span className="text-red-500">*</span>
                  </label>
                  <input
                    required
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat your password"
                    className={inputClass}
                    autoComplete="new-password"
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
                  className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-2.5 text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors mt-2"
                >
                  {status === "loading" ? (
                    <><Loader2 size={14} className="animate-spin" /> Creating account…</>
                  ) : (
                    <>Continue <span className="ml-0.5">→</span></>
                  )}
                </button>
              </form>

              <p className="text-center text-sm text-slate-500 mt-6">
                Already have an account?{" "}
                <button onClick={onBackToLogin} className="text-blue-600 font-semibold hover:underline">
                  Sign in
                </button>
              </p>
            </>
          ) : (
            <>
              <div className="flex items-center gap-3 mb-1">
                <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
                  <CheckCircle2 size={16} className="text-emerald-600" />
                </div>
                <h1 className="text-xl font-bold text-slate-900">Account created!</h1>
              </div>
              <p className="text-sm text-slate-500 mb-5">
                Tell your AI agent about your business so it can answer customer questions accurately.
                You can add more context later in the <strong>Business Context</strong> section.
              </p>

              {/* Saved context preview */}
              {contextItems.length > 0 && (
                <div className="mb-4 space-y-2">
                  {contextItems.map((item, i) => (
                    <div key={i} className="flex items-start gap-2 bg-slate-50 border border-slate-100 rounded-lg px-3 py-2.5">
                      <CheckCircle2 size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-700">{item.label}</p>
                        <p className="text-xs text-slate-400 truncate">{item.content}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Add context form */}
              <div className="border border-slate-200 rounded-xl p-4 mb-5 space-y-3 bg-slate-50/50">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Add a context item</p>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Topic Label</label>
                  <input
                    value={ctxLabel}
                    onChange={(e) => setCtxLabel(e.target.value)}
                    placeholder="e.g. Company Overview, Products, Hours…"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Content</label>
                  <textarea
                    rows={3}
                    value={ctxContent}
                    onChange={(e) => setCtxContent(e.target.value)}
                    placeholder="Describe this topic. The AI agent will use this during live calls…"
                    className={`${inputClass} resize-y`}
                  />
                </div>
                {ctxError && (
                  <div className="flex items-center gap-2 text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm">
                    <AlertCircle size={14} className="shrink-0" /> {ctxError}
                  </div>
                )}
                <button
                  type="button"
                  onClick={handleAddContext}
                  disabled={ctxSaving || !ctxLabel.trim() || !ctxContent.trim()}
                  className="flex items-center gap-2 bg-slate-800 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {ctxSaving ? (
                    <><Loader2 size={13} className="animate-spin" /> Saving…</>
                  ) : (
                    <><CheckCircle2 size={13} /> Add Context Item</>
                  )}
                </button>
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleFinish}
                  className="flex-1 flex items-center justify-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-2.5 text-sm font-semibold hover:bg-blue-700 transition-colors"
                >
                  {contextItems.length > 0 ? "Finish Setup →" : "Go to Dashboard →"}
                </button>
                {contextItems.length === 0 && (
                  <button
                    type="button"
                    onClick={handleFinish}
                    className="px-4 py-2.5 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    Skip for now
                  </button>
                )}
              </div>
            </>
          )}
        </div>
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
  token,
  username,
  onJoinCall,
}: {
  health: Record<ServiceName, HealthResult>;
  refresh: () => void;
  token: string;
  username: string;
  onJoinCall: (convId: string, businessId: string) => void;
}) {
  const services: ServiceName[] = ["audio", "intelligence", "llm"];
  const online = services.filter((s) => health[s].status === "online").length;

  const [tickets, setTickets] = useState<EscalationTicket[]>([]);
  const [loadingTickets, setLoadingTickets] = useState(true);
  const [actioningId, setActioningId] = useState<string | null>(null);
  const [viewingTicket, setViewingTicket] = useState<EscalationTicket | null>(null);

  const fetchTickets = async () => {
    try {
      const data = await listEscalationQueue(token);
      setTickets(data);
    } catch {
      // silently ignore poll errors
    } finally {
      setLoadingTickets(false);
    }
  };

  useEffect(() => {
    fetchTickets();
    const id = setInterval(fetchTickets, 10_000);
    return () => clearInterval(id);
  }, [token]);

  // SSE: real-time ticket push — supplements the 10s poll
  useEffect(() => {
    const es = new EventSource(
      `${SERVICES.audio}/escalation-queue/stream?token=${encodeURIComponent(token)}`
    );
    es.onmessage = (e) => {
      if (e.data === "connected") return;
      try {
        const ticket = JSON.parse(e.data) as EscalationTicket;
        setTickets((prev) => {
          if (prev.some((t) => t.id === ticket.id)) return prev;
          return [ticket, ...prev];
        });
      } catch {
        // ignore parse errors
      }
    };
    es.onerror = () => {
      es.close();
    };
    return () => es.close();
  }, [token]);

  const handleClaim = async (ticketId: string) => {
    setActioningId(ticketId);
    try {
      await updateEscalationTicket(token, ticketId, { status: "claimed", claimed_by: username });
      await fetchTickets();
      if (viewingTicket?.id === ticketId) {
        const updated = await getEscalationTicket(token, ticketId);
        setViewingTicket(updated);
      }
    } finally {
      setActioningId(null);
    }
  };

  const handleResolve = async (ticketId: string) => {
    setActioningId(ticketId);
    try {
      await updateEscalationTicket(token, ticketId, { status: "resolved" });
      await fetchTickets();
      if (viewingTicket?.id === ticketId) {
        setViewingTicket(null);
      }
    } finally {
      setActioningId(null);
    }
  };

  const handleViewTicket = async (ticketId: string) => {
    try {
      const t = await getEscalationTicket(token, ticketId);
      setViewingTicket(t);
    } catch {
      // ignore
    }
  };

  const pendingTickets = tickets.filter((t) => t.status === "pending");
  const claimedTickets = tickets.filter((t) => t.status === "claimed");
  const resolvedToday = tickets.filter(
    (t) =>
      t.status === "resolved" &&
      new Date(t.resolved_at ?? t.created_at).toDateString() === new Date().toDateString()
  ).length;

  const priorityBadgeClass = (p: EscalationTicket["priority"]) => {
    if (p === "high") return "bg-red-100 text-red-700";
    if (p === "low") return "bg-green-100 text-green-700";
    return "bg-amber-100 text-amber-700";
  }

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
            <div className="text-3xl font-bold text-blue-600">{claimedTickets.length}</div>
            <div className="text-sm text-slate-500 mt-1 flex items-center gap-1.5">
              <User size={13} /> In Progress
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
                    <th className="pb-2 font-medium pr-4">Priority</th>
                    <th className="pb-2 font-medium pr-4">Rule</th>
                    <th className="pb-2 font-medium pr-4">Time</th>
                    <th className="pb-2 font-medium pr-4">Status</th>
                    <th className="pb-2 font-medium">Actions</th>
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
                      <td className="py-3 pr-4">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${priorityBadgeClass(ticket.priority)}`}>
                          {ticket.priority}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-xs text-slate-400">
                        {ticket.rule_triggered ?? "—"}
                      </td>
                      <td className="py-3 pr-4 text-xs text-slate-400 whitespace-nowrap">
                        {new Date(ticket.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge
                          variant={
                            ticket.status === "pending"
                              ? "warning"
                              : ticket.status === "claimed"
                              ? "default"
                              : "online"
                          }
                        >
                          {ticket.status}
                        </Badge>
                      </td>
                      <td className="py-3 flex items-center gap-2">
                        <button
                          onClick={() => handleViewTicket(ticket.id)}
                          className="text-xs text-slate-500 hover:text-slate-800 font-medium border border-slate-200 rounded px-2 py-0.5 hover:bg-slate-50"
                        >
                          View
                        </button>
                        {ticket.status === "pending" && (
                          <button
                            disabled={actioningId === ticket.id}
                            onClick={() => handleClaim(ticket.id)}
                            className="text-xs text-blue-600 hover:text-blue-800 font-medium disabled:opacity-50"
                          >
                            Claim
                          </button>
                        )}
                        {ticket.status === "claimed" && ticket.claimed_by === username && (
                          <button
                            disabled={actioningId === ticket.id}
                            onClick={() => handleResolve(ticket.id)}
                            className="text-xs text-emerald-600 hover:text-emerald-800 font-medium disabled:opacity-50"
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
      {viewingTicket && (
        <TicketDetailModal
          ticket={viewingTicket}
          onClose={() => setViewingTicket(null)}
          onJoinCall={onJoinCall}
          onClaim={handleClaim}
          onResolve={handleResolve}
          username={username}
        />
      )}
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
}: {
  businessId: string;
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
                  <input required type="number" min={0} value={startMs} onChange={(e) => setStartMs(e.target.value)} className={inputClass} placeholder="0" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">End ms</label>
                  <input required type="number" min={0} value={endMs} onChange={(e) => setEndMs(e.target.value)} className={inputClass} placeholder="5000" />
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
  const [editIsAlert, setEditIsAlert] = useState(false);
  const [editExpiresAt, setEditExpiresAt] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const [apiError, setApiError] = useState("");
  const [isAlert, setIsAlert] = useState(false);
  const [expiresAt, setExpiresAt] = useState("");
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
    if (isAlert && !expiresAt) return;  // expiry required for alerts
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
        isAlert,
        isAlert && expiresAt ? new Date(expiresAt).toISOString() : undefined,
      );
      setItems((prev) => [...prev, item]);
      setLabel("");
      setContent("");
      setFileInfo(null);
      setRefineWithAi(false);
      setIsAlert(false);
      setExpiresAt("");
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
    setEditIsAlert(item.is_alert ?? false);
    // Convert stored UTC ISO to local datetime-local value for the input
    if (item.expires_at) {
      const d = new Date(item.expires_at);
      const pad = (n: number) => String(n).padStart(2, "0");
      setEditExpiresAt(
        `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
      );
    } else {
      setEditExpiresAt("");
    }
  };

  const handleSaveEdit = async (id: string) => {
    setSavingEdit(true);
    setApiError("");
    try {
      const updated = await updateContextItem(
        token,
        id,
        {
          label: editLabel,
          content: editContent,
          is_alert: editIsAlert,
          expires_at: editIsAlert && editExpiresAt
            ? new Date(editExpiresAt).toISOString()
            : null,
        },
        editRefine,
      );
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
                  aria-label="Upload context file"
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

            {/* Temporary Alert toggle */}
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={isAlert}
                onChange={(e) => setIsAlert(e.target.checked)}
                className="rounded"
              />
              <span className="flex items-center gap-1.5 text-sm text-slate-700">
                <AlertCircle size={13} className="text-orange-500" /> Temporary Alert
              </span>
            </label>
            {isAlert && (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Alert Expiry <span className="text-red-500">*</span>
                </label>
                <input
                  type="datetime-local"
                  value={expiresAt}
                  onChange={(e) => setExpiresAt(e.target.value)}
                  className={inputClass}
                  title="Alert expiry date and time"
                />
                <p className="text-xs text-slate-400 mt-1">
                  Alert will stop being sent to the AI after this time.
                </p>
              </div>
            )}

            <button
              onClick={handleAdd}
              disabled={saving || !label.trim() || (mode === "text" ? !content.trim() : !fileInfo) || (isAlert && !expiresAt)}
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
              {items.map((item) => {
                const isExpired = item.is_alert && item.expires_at
                  ? new Date(item.expires_at) < new Date()
                  : false;
                return (
                <Card key={item.id} className={`border ${isExpired ? "border-slate-100 opacity-60" : "border-slate-100"}`}>
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
                          placeholder="Business context content…"
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
                        {/* Alert toggle in edit form */}
                        <label className="flex items-center gap-2 cursor-pointer select-none text-sm text-slate-700">
                          <input
                            type="checkbox"
                            checked={editIsAlert}
                            onChange={(e) => setEditIsAlert(e.target.checked)}
                            className="rounded"
                          />
                          <AlertCircle size={12} className="text-orange-500" /> Temporary Alert
                        </label>
                        {editIsAlert && (
                          <div>
                            <label className="block text-xs font-medium text-slate-700 mb-1">
                              Alert Expiry <span className="text-red-500">*</span>
                            </label>
                            <input
                              type="datetime-local"
                              value={editExpiresAt}
                              onChange={(e) => setEditExpiresAt(e.target.value)}
                              className={inputClass}
                              title="Alert expiry date and time"
                            />
                          </div>
                        )}
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
                            {item.is_alert && (
                              <span className="inline-flex items-center gap-0.5 text-xs font-medium text-orange-600 bg-orange-50 border border-orange-200 rounded px-1.5 py-0.5 shrink-0">
                                <AlertCircle size={10} /> Alert
                              </span>
                            )}
                            {isExpired && (
                              <span className="inline-flex items-center text-xs font-medium text-red-600 bg-red-50 border border-red-200 rounded px-1.5 py-0.5 shrink-0">
                                Expired
                              </span>
                            )}
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
                        {item.is_alert && item.expires_at && (
                          <p className="mt-1 text-xs text-orange-400">
                            Expires: {new Date(item.expires_at).toLocaleString()}
                          </p>
                        )}
                        <p className="mt-1.5 text-xs text-slate-300">
                          {new Date(item.created_at).toLocaleString()}
                        </p>
                      </>
                    )}
                  </CardContent>
                </Card>
                );
              })}
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
  initialConvId,
}: {
  businessId: string;
  token: string;
  initialConvId?: string;
}) {
  type CallStatus = "idle" | "connecting" | "active" | "listening" | "processing" | "speaking" | "ended" | "error" | "escalated";

  const [callStatus, setCallStatus] = useState<CallStatus>("idle");
  const [convId, setConvId] = useState(initialConvId ?? "");
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
      if (chatResp.escalated) {
        setCallStatus("escalated");
        setStatusLabel("Escalated — human agent joining");
      }
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

  const isLive = callStatus !== "idle" && callStatus !== "ended" && callStatus !== "error" && callStatus !== "escalated";
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
    escalated: "bg-purple-500 animate-pulse",
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

            {/* Escalation banner */}
            {callStatus === "escalated" && (
              <div className="bg-purple-50 border border-purple-200 rounded-xl px-4 py-3 text-sm text-purple-800 font-medium text-center">
                🎫 A support ticket has been opened. A human agent will join shortly — please hold the line.
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
// Ticket Detail Modal
// ──────────────────────────────────────────────────────────────────────────────

function TicketDetailModal({
  ticket,
  onClose,
  onJoinCall,
  onClaim,
  onResolve,
  username,
}: {
  ticket: EscalationTicket;
  onClose: () => void;
  onJoinCall: (convId: string, businessId: string) => void;
  onClaim: (id: string) => void;
  onResolve: (id: string) => void;
  username: string;
}) {
  const priorityBadgeClass = (p: EscalationTicket["priority"]) => {
    if (p === "high") return "bg-red-100 text-red-700";
    if (p === "low") return "bg-green-100 text-green-700";
    return "bg-amber-100 text-amber-700";
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[80vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-6 py-4 border-b border-slate-100">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${priorityBadgeClass(ticket.priority)}`}>
                {ticket.priority}
              </span>
              <Badge
                variant={
                  ticket.status === "pending" ? "warning" : ticket.status === "claimed" ? "default" : "online"
                }
              >
                {ticket.status}
              </Badge>
            </div>
            <h2 className="text-base font-semibold text-slate-900 leading-snug">{ticket.reason}</h2>
            {ticket.rule_triggered && (
              <p className="text-xs text-slate-400 mt-0.5">Rule: {ticket.rule_triggered}</p>
            )}
            <p className="text-xs text-slate-400 mt-0.5">
              {new Date(ticket.created_at).toLocaleString()}
              {ticket.conv_id && <> · Conv: <span className="font-mono">{ticket.conv_id}</span></>}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 shrink-0 mt-0.5"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Transcript */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
          {(ticket.conversation_history ?? []).length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-6">No conversation history recorded.</p>
          ) : (
            (ticket.conversation_history ?? []).map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[78%] rounded-2xl px-4 py-2 text-sm leading-relaxed ${
                    msg.role === "assistant"
                      ? "bg-blue-600 text-white rounded-bl-sm"
                      : "bg-slate-100 text-slate-800 rounded-br-sm"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-100">
          {ticket.status === "pending" && (
            <button
              onClick={() => onClaim(ticket.id)}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              Claim
            </button>
          )}
          {ticket.status === "claimed" && ticket.claimed_by === username && (
            <button
              onClick={() => onResolve(ticket.id)}
              className="text-sm text-emerald-600 hover:text-emerald-800 font-medium"
            >
              Resolve
            </button>
          )}
          {ticket.status !== "resolved" && ticket.conv_id && (
            <button
              onClick={() => { onJoinCall(ticket.conv_id!, ticket.business_id); onClose(); }}
              className="text-sm bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg transition-colors"
            >
              Join as Agent
            </button>
          )}
          <button
            onClick={onClose}
            className="text-sm text-slate-500 hover:text-slate-700 font-medium px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Escalation Rules page
// ──────────────────────────────────────────────────────────────────────────────

function EscalationRulesPage({ token }: { token: string }) {
  const [rules, setRules] = useState<EscalationRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [ruleText, setRuleText] = useState("");
  const [priority, setPriority] = useState<"high" | "medium" | "low">("medium");
  const [aiRefine, setAiRefine] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [editPriority, setEditPriority] = useState<"high" | "medium" | "low">("medium");
  const [apiError, setApiError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const data = await listEscalationRules(token);
      setRules(data);
    } catch {
      setApiError("Failed to load rules.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleAdd = async () => {
    if (!ruleText.trim()) return;
    setSaving(true);
    setApiError("");
    try {
      await createEscalationRule(token, { rule_text: ruleText.trim(), priority }, aiRefine);
      setRuleText("");
      setPriority("medium");
      setAiRefine(false);
      await load();
    } catch {
      setApiError("Failed to save rule.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteEscalationRule(token, id);
      await load();
    } catch {
      setApiError("Failed to delete rule.");
    }
  };

  const handleSaveEdit = async (id: string) => {
    try {
      await updateEscalationRule(token, id, { rule_text: editText.trim(), priority: editPriority });
      setEditingId(null);
      await load();
    } catch {
      setApiError("Failed to update rule.");
    }
  };

  const priorityColor = (p: EscalationRule["priority"]) => {
    if (p === "high") return "bg-red-100 text-red-700";
    if (p === "low") return "bg-green-100 text-green-700";
    return "bg-amber-100 text-amber-700";
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Escalation Rules</h1>
        <p className="text-sm text-slate-500 mt-1">Define when the AI should escalate calls to a human agent</p>
      </div>
      {apiError && <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">{apiError}</div>}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Add rule form */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Add New Rule</CardTitle>
            <CardDescription>Describe when the AI should hand off to a human</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Rule description</label>
              <textarea
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={4}
                placeholder="e.g. Escalate if the customer mentions billing disputes or requests a refund above $100"
                value={ruleText}
                onChange={(e) => setRuleText(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Priority</label>
              <select
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={priority}
                onChange={(e) => setPriority(e.target.value as "high" | "medium" | "low")}
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                checked={aiRefine}
                onChange={(e) => setAiRefine(e.target.checked)}
                className="rounded"
              />
              AI-refine rule for better LLM understanding
            </label>
            <button
              disabled={saving || !ruleText.trim()}
              onClick={handleAdd}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 rounded-lg disabled:opacity-50 transition-colors"
            >
              {saving ? "Saving…" : "Add Rule"}
            </button>
          </CardContent>
        </Card>

        {/* Rules list */}
        <div className="space-y-3">
          {loading ? (
            <div className="flex items-center justify-center py-10 text-slate-400">
              <Spinner className="w-5 h-5" />
            </div>
          ) : rules.length === 0 ? (
            <Card>
              <CardContent className="py-10 text-center text-slate-400 text-sm">
                No rules yet. Add one to get started.
              </CardContent>
            </Card>
          ) : (
            rules.map((rule) => (
              <Card key={rule.id}>
                <CardContent className="pt-4 pb-3">
                  {editingId === rule.id ? (
                    <div className="space-y-2">
                      <textarea
                        className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                        rows={3}
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                      />
                      <select
                        className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        value={editPriority}
                        onChange={(e) => setEditPriority(e.target.value as "high" | "medium" | "low")}
                      >
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                      </select>
                      <div className="flex gap-2">
                        <button onClick={() => handleSaveEdit(rule.id)} className="text-xs bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700">Save</button>
                        <button onClick={() => setEditingId(null)} className="text-xs text-slate-500 hover:text-slate-700 px-3 py-1.5 rounded-lg border border-slate-200">Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${priorityColor(rule.priority)}`}>{rule.priority}</span>
                        <div className="flex gap-1.5">
                          <button onClick={() => { setEditingId(rule.id); setEditText(rule.rule_text); setEditPriority(rule.priority); }} className="text-xs text-slate-400 hover:text-blue-600">Edit</button>
                          <button onClick={() => handleDelete(rule.id)} className="text-xs text-slate-400 hover:text-red-600">Delete</button>
                        </div>
                      </div>
                      <p className="text-sm text-slate-700">{rule.rule_text}</p>
                      {rule.ai_refined_text && rule.ai_refined_text !== rule.rule_text && (
                        <div className="mt-2 pt-2 border-t border-slate-100">
                          <p className="text-xs text-slate-400 mb-1">AI-refined version:</p>
                          <p className="text-xs text-slate-500 italic">{rule.ai_refined_text}</p>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))
          )}
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
  const [authView, setAuthView] = useState<"login" | "register">("login");
  const { health, refresh } = useServiceHealth();
  const [joinConvId, setJoinConvId] = useState<string>("");
  const [auth, setAuth] = useState<AuthState | null>(() => {
    try {
      const stored = localStorage.getItem("callsup_auth");
      return stored ? (JSON.parse(stored) as AuthState) : null;
    } catch {
      return null;
    }
  });

  const handleLogout = () => {
    localStorage.removeItem("callsup_auth");
    setAuth(null);
  };

  const handleJoinCall = (convId: string, _businessId: string) => {
    setJoinConvId(convId);
    setPage("simulation");
  };

  if (!auth) {
    if (authView === "register") {
      return <RegisterPage onAuth={setAuth} onBackToLogin={() => setAuthView("login")} />;
    }
    return <LoginPage onAuth={setAuth} onGoToRegister={() => setAuthView("register")} />;
  }

  const navItems: { id: Page; label: string; icon: React.ReactNode }[] = [
    { id: "dashboard", label: "Dashboard", icon: <LayoutDashboard size={16} /> },
    { id: "transcripts", label: "Transcripts", icon: <FileText size={16} /> },
    { id: "intelligence", label: "AI Demo", icon: <Zap size={16} /> },
    { id: "context", label: "Business Context", icon: <Building2 size={16} /> },
    { id: "simulation", label: "Call Simulation", icon: <MessageSquare size={16} /> },
    { id: "escalation-rules", label: "Escalation Rules", icon: <ShieldAlert size={16} /> },
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
              <span className="text-xs text-slate-400 truncate">{auth.businessName || auth.username}</span>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-slate-400 hover:text-red-400 hover:bg-slate-800 px-3 py-1.5 rounded-lg text-sm transition-colors"
              title="Sign out"
            >
              <LogOut size={14} />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 p-8 overflow-auto min-w-0">
        {page === "dashboard" && <DashboardPage health={health} refresh={refresh} token={auth.token} username={auth.username} onJoinCall={handleJoinCall} />}
        {page === "transcripts" && <TranscriptsPage />}
        {page === "intelligence" && <IntelligencePage businessId={auth.businessId} />}
        {page === "context" && <BusinessContextPage token={auth.token} />}
        {page === "simulation" && <CallSimulationPage businessId={auth.businessId} token={auth.token} initialConvId={joinConvId} />}
        {page === "escalation-rules" && <EscalationRulesPage token={auth.token} />}
      </main>
    </div>
  );
}

