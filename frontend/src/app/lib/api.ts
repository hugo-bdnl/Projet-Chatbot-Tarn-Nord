/**
 * Client HTTP du back-end du chatbot territorial.
 *
 * Contrat : README.md a la racine du depot, section « Contrat front <-> back ».
 * L'URL de l'API se configure avec VITE_API_URL (defaut : http://localhost:8000).
 * Les endpoints /admin/* attendent l'en-tete X-API-Key quand CHATBOT_API_KEY est
 * definie cote serveur ; la cle est saisie dans le back-office et gardee en local.
 */

const RAW_BASE = (import.meta as any).env?.VITE_API_URL ?? "http://localhost:8000";

export const API_BASE_URL: string = String(RAW_BASE).replace(/\/+$/, "");

const ADMIN_KEY_STORAGE = "chatbot.adminApiKey";
const SESSION_STORAGE = "chatbot.sessionId";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Cle d'administration saisie par l'utilisateur (jamais ecrite dans le code). */
export function getAdminKey(): string {
  try {
    return window.localStorage.getItem(ADMIN_KEY_STORAGE) ?? "";
  } catch {
    return "";
  }
}

export function setAdminKey(key: string): void {
  try {
    if (key) {
      window.localStorage.setItem(ADMIN_KEY_STORAGE, key);
    } else {
      window.localStorage.removeItem(ADMIN_KEY_STORAGE);
    }
  } catch {
    /* stockage indisponible : la cle vaudra pour la duree de la page */
  }
}

/**
 * Identifiant de session anonyme, tire au hasard et garde le temps de l'onglet.
 * Le serveur ne le stocke jamais tel quel : il en garde une empreinte SHA-256 salee
 * (REQ-FUNC.4), uniquement pour compter les visiteurs distincts.
 */
export function getSessionId(): string {
  try {
    const existing = window.sessionStorage.getItem(SESSION_STORAGE);
    if (existing) return existing;
    const fresh =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `s-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    window.sessionStorage.setItem(SESSION_STORAGE, fresh);
    return fresh;
  } catch {
    return `s-${Date.now()}`;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  admin?: boolean;
  query?: Record<string, string | number | boolean | undefined | null>;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.admin) {
    const key = getAdminKey();
    if (key) headers["X-API-Key"] = key;
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError(
      `Service injoignable (${API_BASE_URL}). Verifiez que le back-end est demarre.`,
      0,
    );
  }

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      if (payload && payload.detail) {
        detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
      }
    } catch {
      /* corps non JSON : on garde le code HTTP */
    }
    if (response.status === 401) detail = "Cle d'administration invalide ou absente.";
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/* ------------------------------------------------------------------ types */

export type SearchMode = "semantic" | "keyword" | "hybrid";
export type Intent = "orientation" | "organization" | "document" | "no_answer";

export interface Site {
  id?: number;
  label: string;
  address: string;
  postal_code: string;
  city: string;
}

export interface Contact {
  id?: number;
  last_name: string;
  first_name: string;
  role: string;
  email: string;
  phone: string;
}

export interface Organization {
  id: number;
  name: string;
  description: string;
  website: string;
  keywords: string[];
  domains: string[];
  sites: Site[];
  contacts: Contact[];
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OrganizationResult extends Organization {
  score: number;
}

export interface OrganizationInput {
  name: string;
  description: string;
  website: string;
  keywords: string[];
  domains: string[];
  sites: Site[];
  contacts: Contact[];
  active: boolean;
}

export interface OrganizationList {
  total: number;
  items: Organization[];
}

export interface Domain {
  id: number;
  name: string;
  description: string;
  organizations: number;
}

export interface DocumentExtract {
  title: string;
  source: string;
  section: string;
  text: string;
  score: number;
}

export interface AskResponse {
  question: string;
  mode: SearchMode;
  intent: Intent;
  answered: boolean;
  answer: string;
  category: string | null;
  score: number | null;
  organizations: OrganizationResult[];
  documents: DocumentExtract[];
  suggestions: string[];
  query_id: number | null;
  latency_ms: number;
}

export interface PublicConfig {
  name: string;
  welcome_message: string;
  initial_suggestions: string[];
  suggestions_enabled: boolean;
}

export interface Category {
  name: string;
  keywords: string[];
  example_question: string;
}

export interface ChatbotConfig {
  name: string;
  welcome_message: string;
  initial_suggestions: string[];
  suggestions_enabled: boolean;
  orientation_enabled: boolean;
  analytics_enabled: boolean;
  max_organizations: number;
  orientation_intro: string;
  orientation_outro: string;
  no_answer_message: string;
  categories: Category[];
}

export interface PeriodTotals {
  conversations: number;
  unique_sessions: number;
  answered: number;
  answer_rate: number | null;
  feedback_count: number;
  satisfaction_rate: number | null;
  avg_latency_ms: number | null;
}

export interface AnalyticsSummary {
  days: number;
  since: string;
  totals: PeriodTotals;
  previous: PeriodTotals;
  per_day: Array<{ date: string; count: number }>;
  categories: Array<{ name: string; count: number }>;
  top_questions: Array<{ question: string; count: number }>;
  unanswered_questions: Array<{ question: string; count: number }>;
  top_organizations: Array<{ name: string; count: number }>;
  latency_by_hour: Array<{ hour: number; avg_latency_ms: number; count: number }>;
}

export interface Health {
  status: string;
  version: string;
  model: string;
  documents: number;
  organizations: number;
  passages: number;
}

/* ------------------------------------------------------- endpoints publics */

export function getHealth(): Promise<Health> {
  return request<Health>("/health");
}

export function getPublicConfig(): Promise<PublicConfig> {
  return request<PublicConfig>("/config");
}

export function ask(question: string, options: { mode?: SearchMode } = {}): Promise<AskResponse> {
  return request<AskResponse>("/ask", {
    method: "POST",
    body: { question, session_id: getSessionId(), mode: options.mode },
  });
}

export function sendFeedback(queryId: number, helpful: boolean, comment?: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/feedback", {
    method: "POST",
    body: { query_id: queryId, helpful, comment },
  });
}

export function listDomains(): Promise<Domain[]> {
  return request<Domain[]>("/domains");
}

/* --------------------------------------------------------- endpoints admin */

export function listOrganizations(
  params: { q?: string; domain?: string; active?: boolean; limit?: number; offset?: number } = {},
): Promise<OrganizationList> {
  return request<OrganizationList>("/admin/organizations", { admin: true, query: params });
}

export function createOrganization(payload: OrganizationInput): Promise<Organization> {
  return request<Organization>("/admin/organizations", { method: "POST", body: payload, admin: true });
}

export function updateOrganization(id: number, payload: OrganizationInput): Promise<Organization> {
  return request<Organization>(`/admin/organizations/${id}`, { method: "PUT", body: payload, admin: true });
}

export function deleteOrganization(id: number): Promise<void> {
  return request<void>(`/admin/organizations/${id}`, { method: "DELETE", admin: true });
}

export function getAnalytics(days = 7): Promise<AnalyticsSummary> {
  return request<AnalyticsSummary>("/admin/analytics", { admin: true, query: { days } });
}

export function getAdminConfig(): Promise<ChatbotConfig> {
  return request<ChatbotConfig>("/admin/config", { admin: true });
}

export function saveAdminConfig(config: ChatbotConfig): Promise<ChatbotConfig> {
  return request<ChatbotConfig>("/admin/config", { method: "PUT", body: config, admin: true });
}

export function resetAdminConfig(): Promise<ChatbotConfig> {
  return request<ChatbotConfig>("/admin/config/reset", { method: "POST", admin: true });
}

export function reindex(): Promise<{ documents: number; organizations: number; passages: number; seconds: number }> {
  return request("/admin/reindex", { method: "POST", admin: true });
}

/** Message lisible par l'usager pour n'importe quelle erreur remontee du client. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Erreur inconnue";
}
