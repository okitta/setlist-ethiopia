import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: async () => body,
  });
}

afterEach(() => vi.restoreAllMocks());

describe("api client", () => {
  it("sends the X-User header on writes", async () => {
    const fetchMock = mockFetch(200, { performance_id: 1, attending: true, attendance_count: 1 });
    vi.stubGlobal("fetch", fetchMock);

    await api.markAttendance(1, "fan_hana");

    const [, opts] = fetchMock.mock.calls[0];
    expect(opts.method).toBe("POST");
    expect(opts.headers["X-User"]).toBe("fan_hana");
  });

  it("raises a typed ApiError carrying the server code and status", async () => {
    vi.stubGlobal("fetch", mockFetch(403, { code: "forbidden", message: "nope" }));

    await expect(api.addSong(1, "Tizita", "fan_hana")).rejects.toMatchObject({
      code: "forbidden",
      status: 403,
    });
    await expect(api.addSong(1, "Tizita", "fan_hana")).rejects.toBeInstanceOf(ApiError);
  });
});
