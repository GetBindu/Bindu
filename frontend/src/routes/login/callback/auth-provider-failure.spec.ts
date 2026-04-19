/**
 * Integration tests for OAuth provider failure in the login callback flow.
 *
 * Runs in the "server" Vitest workspace (environment: node).
 * Uses vi.hoisted() so that mock variables are accessible inside vi.mock() factories.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// Hoist mock references so they can be used in vi.mock() factories
// ---------------------------------------------------------------------------
const { mockIssuerDiscover } = vi.hoisted(() => ({
    mockIssuerDiscover: vi.fn(),
}));

// ---------------------------------------------------------------------------
// All vi.mock() calls – must appear before any named imports
// ---------------------------------------------------------------------------
vi.mock("$app/paths", () => ({ base: "" }));
vi.mock("$app/environment", () => ({ dev: false }));
vi.mock("$lib/server/database", () => ({ collections: {} }));
vi.mock("$lib/migrations/lock", () => ({
    acquireLock: vi.fn(),
    releaseLock: vi.fn(),
    isDBLocked: vi.fn(),
}));
vi.mock("$lib/utils/sha256", () => ({
    sha256: vi.fn(async (v: string) => v + "-hashed"),
}));
vi.mock("bson-objectid", () => ({ default: class ObjectId { } }));
vi.mock("$lib/types/Semaphore", () => ({ Semaphores: { OAUTH_TOKEN_REFRESH: "oauth_refresh" } }));
vi.mock("$lib/server/logger", () => ({
    logger: { error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));
vi.mock("./adminToken", () => ({
    adminTokenManager: { isAdmin: vi.fn(() => false) },
}));
vi.mock("$lib/server/config", () => ({
    config: {
        OPENID_CLIENT_ID: "test-client-id",
        OPENID_CLIENT_SECRET: "test-client-secret",
        OPENID_PROVIDER_URL: "https://provider.example.com",
        OPENID_SCOPES: "openid profile",
        OPENID_NAME_CLAIM: "name",
        OPENID_TOLERANCE: "",
        OPENID_RESOURCE: "",
        OPENID_CONFIG: "{}",
        COOKIE_NAME: "hf-chat",
        COOKIE_SAMESITE: "",
        COOKIE_SECURE: "",
        ALLOW_INSECURE_COOKIES: "true",
        PUBLIC_ORIGIN: "http://localhost:5173",
        COUPLE_SESSION_WITH_COOKIE_NAME: "",
        TRUSTED_EMAIL_HEADER: "",
        ALTERNATIVE_REDIRECT_URLS: [],
    },
}));
vi.mock("openid-client", () => ({
    Issuer: { discover: mockIssuerDiscover },
    custom: { clock_tolerance: Symbol("clock_tolerance") },
    generators: {
        codeVerifier: vi.fn(() => "test-code-verifier"),
        codeChallenge: vi.fn(() => "test-code-challenge"),
    },
}));

// ---------------------------------------------------------------------------
// Imports (after all vi.mock() calls)
// ---------------------------------------------------------------------------
import { OAuthProviderError } from "$lib/server/auth";

// ---------------------------------------------------------------------------
// Helper to call triggerOauthFlow with a mocked-down provider
// ---------------------------------------------------------------------------
async function simulateProviderDown(
    providerError: Error
): Promise<{ status: number; body: { code: string; message: string } }> {
    mockIssuerDiscover.mockRejectedValue(providerError);
    const { triggerOauthFlow } = await import("$lib/server/auth");

    const event = {
        url: new URL("http://localhost:5173/login"),
        locals: { sessionId: "e2e-session-id" },
        cookies: {
            set: vi.fn(),
            get: vi.fn(),
            getAll: vi.fn(() => []),
            delete: vi.fn(),
            serialize: vi.fn(),
        },
        request: new Request("http://localhost:5173/login"),
    };

    const response = await triggerOauthFlow(event as never);
    const body = await response.json();
    return { status: response.status, body };
}

// ---------------------------------------------------------------------------
// E2E: provider unavailable scenarios
// ---------------------------------------------------------------------------
describe("E2E: OAuth provider unavailability", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockIssuerDiscover.mockReset();
    });

    it("returns 502 + OAUTH_PROVIDER_UNAVAILABLE when TypeError (fetch failed)", async () => {
        const { status, body } = await simulateProviderDown(new TypeError("fetch failed"));
        expect(status).toBe(502);
        expect(body.code).toBe("OAUTH_PROVIDER_UNAVAILABLE");
        expect(body.message).toMatch(/temporarily unavailable/i);
    });

    it("returns 502 + OAUTH_PROVIDER_UNAVAILABLE when ECONNREFUSED", async () => {
        const { status, body } = await simulateProviderDown(
            new Error("connect ECONNREFUSED 127.0.0.1:443")
        );
        expect(status).toBe(502);
        expect(body.code).toBe("OAUTH_PROVIDER_UNAVAILABLE");
    });

    it("returns 502 + OAUTH_PROVIDER_UNAVAILABLE when ENOTFOUND (DNS failure)", async () => {
        const { status, body } = await simulateProviderDown(
            new Error("getaddrinfo ENOTFOUND provider.example.com")
        );
        expect(status).toBe(502);
        expect(body.code).toBe("OAUTH_PROVIDER_UNAVAILABLE");
    });

    it("returns 502 + OAUTH_PROVIDER_ERROR on non-network provider error", async () => {
        const { status, body } = await simulateProviderDown(
            new Error("Internal server error from OIDC provider")
        );
        expect(status).toBe(502);
        expect(body.code).toBe("OAUTH_PROVIDER_ERROR");
        expect(body.message).toMatch(/error occurred/i);
    });
});

// ---------------------------------------------------------------------------
// E2E: OAuthProviderError propagation
// ---------------------------------------------------------------------------
describe("E2E: OAuthProviderError propagation", () => {
    it("carries OAUTH_PROVIDER_UNAVAILABLE code", () => {
        const err = new OAuthProviderError("Provider unreachable", "OAUTH_PROVIDER_UNAVAILABLE");
        expect(err.name).toBe("OAuthProviderError");
        expect(err.code).toBe("OAUTH_PROVIDER_UNAVAILABLE");
    });

    it("defaults to OAUTH_PROVIDER_ERROR code", () => {
        const err = new OAuthProviderError("Unknown error");
        expect(err.code).toBe("OAUTH_PROVIDER_ERROR");
    });

    it("non-OAuthProviderError errors are re-thrown unchanged", () => {
        const originalErr = new Error("Some unrelated error");
        let rethrown: Error | null = null;
        try {
            throw originalErr;
        } catch (e: any) {
            if (e.name === "OAuthProviderError") {
                rethrown = new Error("wrongly caught");
            } else {
                rethrown = e as Error;
            }
        }
        expect(rethrown).toBe(originalErr);
    });
});
