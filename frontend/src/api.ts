import type {
  Artist,
  Attendance,
  Features,
  PerformanceDetail,
  Performance,
  Revision,
} from "./types";

/**
 * Thin API client. It attaches the current user's handle as the `X-User` header —
 * a stand-in for real session auth in slice 1 (see backend/app/dependencies.py).
 * Server-side authorisation is still the source of truth; the UI only reflects it.
 */

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, opts: RequestInit = {}, user?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (user) headers["X-User"] = user;
  const res = await fetch(path, { ...opts, headers: { ...headers, ...(opts.headers || {}) } });
  if (!res.ok) {
    let code = "error";
    let message = res.statusText;
    try {
      const body = await res.json();
      code = body.code ?? code;
      message = body.message ?? body.detail ?? message;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(code, message, res.status);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  features: () => request<Features>("/features"),
  searchArtists: (q: string) =>
    request<Artist[]>(`/api/v1/artists?q=${encodeURIComponent(q)}`),
  performances: (artistId: number) =>
    request<Performance[]>(`/api/v1/artists/${artistId}/performances`),
  performance: (id: number) => request<PerformanceDetail>(`/api/v1/performances/${id}`),
  revisions: (id: number) => request<Revision[]>(`/api/v1/performances/${id}/revisions`),
  markAttendance: (id: number, user: string) =>
    request<Attendance>(`/api/v1/performances/${id}/attendance`, { method: "POST" }, user),
  unmarkAttendance: (id: number, user: string) =>
    request<Attendance>(`/api/v1/performances/${id}/attendance`, { method: "DELETE" }, user),
  addSong: (id: number, title: string, user: string) =>
    request<PerformanceDetail>(
      `/api/v1/performances/${id}/songs`,
      { method: "POST", body: JSON.stringify({ title }) },
      user,
    ),
  report: (entityId: number, reason: string, user: string) =>
    request(
      "/api/v1/reports",
      {
        method: "POST",
        body: JSON.stringify({
          entity_type: "performance",
          entity_id: entityId,
          reason,
        }),
      },
      user,
    ),
};
