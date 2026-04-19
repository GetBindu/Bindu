/**
 * Unit tests for OAuth provider error handling in auth.ts
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
vi.mock("$lib/server/database", () => ({ collections: {} }));
vi.mock("./adminToken", () => ({
    adminTokenManager: { isAdmin: vi.fn(() => false) },
}));
vi.mock("$lib/server/logger", () => ({
    logger: { error: vi.fn(), info: vi.fn(), warn: vi.fn() },
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
import { OAuthProviderError } from "./auth";

// ---------------------------------------------------------------------------
// OAuthProviderError class tests
// ---------------------------------------------------------------------------
describe("OAuthProviderError", () => {
    it("defaults code to OAUTH_PROVIDER_ERROR", () => {
        const err = new OAuthProviderError("Something went wrong");
        expect(err.code).toBe("OAUTH_PROVIDER_ERROR");
        expect(err.name).toBe("OAuthProviderError");
        expect(err.message).toBe("Something went wrong");
    });

    it("accepts OAUTH_PROVIDER_UNAVAILABLE code", () => {
        const err = new OAuthProviderError("Provider down", "OAUTH_PROVIDER_UNAVAILABLE");
        expect(err.code).toBe("OAUTH_PROVIDER_UNAVAILABLE");
    });

    it("is an instance of Error", () => {
        const err = new OAuthProviderError("test");
        expect(err instanceof Error).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// triggerOauthFlow error handling tests
// ---------------------------------------------------------------------------
describe("triggerOauthFlow – provider failures", () => {
    const makeEvent = () => ({
        url: new URL("http://localhost:5173/login"),
        locals: { sessionId: "test-session-id" },
        cookies: {
            set: vi.fn(),
            get: vi.fn(),
            getAll: vi.fn(() => []),
            delete: vi.fn(),
            serialize: vi.fn(),
        },
        request: new Request("http://localhost:5173/login"),
    });

    beforeEach(() => {
        // Reset module cache to clear auth.ts's module-level lastIssuer cache.
        vi.resetModules();
        vi.clearAllMocks();
        mockIssuerDiscover.mockReset();
    });

    it("returns 502 + OAUTH_PROVIDER_UNAVAILABLE on TypeError (fetch failed)", async () => {
        mockIssuerDiscover.mockRejectedValue(new TypeError("fetch failed"));
        const { triggerOauthFlow } = await import("./auth");
        const response = await triggerOauthFlow(makeEvent() as never);

        expect(response.status).toBe(502);
        const body = await response.json();
        expect(body.code).toBe("OAUTH_PROVIDER_UNAVAILABLE");
        expect(typeof body.message).toBe("string");
    });

    it("returns 502 + OAUTH_PROVIDER_UNAVAILABLE on ECONNREFUSED", async () => {
        mockIssuerDiscover.mockRejectedValue(new Error("connect ECONNREFUSED 127.0.0.1:443"));
        const { triggerOauthFlow } = await import("./auth");
        const response = await triggerOauthFlow(makeEvent() as never);

        expect(response.status).toBe(502);
        const body = await response.json();
        expect(body.code).toBe("OAUTH_PROVIDER_UNAVAILABLE");
    });

    it("returns 502 + OAUTH_PROVIDER_UNAVAILABLE on ENOTFOUND (DNS failure)", async () => {
        mockIssuerDiscover.mockRejectedValue(
            new Error("getaddrinfo ENOTFOUND provider.example.com")
        );
        const { triggerOauthFlow } = await import("./auth");
        const response = await triggerOauthFlow(makeEvent() as never);

        expect(response.status).toBe(502);
        const body = await response.json();
        expect(body.code).toBe("OAUTH_PROVIDER_UNAVAILABLE");
    });

    it("returns 502 + OAUTH_PROVIDER_ERROR on non-network provider error", async () => {
        mockIssuerDiscover.mockRejectedValue(new Error("Invalid discovery document"));
        const { triggerOauthFlow } = await import("./auth");
        const response = await triggerOauthFlow(makeEvent() as never);

        expect(response.status).toBe(502);
        const body = await response.json();
        expect(body.code).toBe("OAUTH_PROVIDER_ERROR");
    });

    it("has Content-Type application/json on error response", async () => {
        mockIssuerDiscover.mockRejectedValue(new Error("provider error"));
        const { triggerOauthFlow } = await import("./auth");
        const response = await triggerOauthFlow(makeEvent() as never);

        expect(response.headers.get("Content-Type")).toContain("application/json");
    });

    it("lets SvelteKit redirect pass through when provider is healthy", async () => {
        mockIssuerDiscover.mockResolvedValue({
            metadata: { id_token_signing_alg_values_supported: ["RS256"] },
            Client: class {
                authorizationUrl() {
                    return "https://provider.example.com/auth?code_challenge=xyz";
                }
            },
        });

        const { triggerOauthFlow } = await import("./auth");
        await expect(triggerOauthFlow(makeEvent() as never)).rejects.toMatchObject({ status: 302 });
    });
});

// ---------------------------------------------------------------------------
// getOIDCUserData error handling tests
// ---------------------------------------------------------------------------
describe("getOIDCUserData – provider failures", () => {
    beforeEach(() => {
        // Reset module cache to clear auth.ts's module-level lastIssuer cache.
        vi.resetModules();
        vi.clearAllMocks();
        mockIssuerDiscover.mockReset();
    });

    it("throws OAuthProviderError OAUTH_PROVIDER_UNAVAILABLE on TypeError fetch failed", async () => {
        mockIssuerDiscover.mockRejectedValue(new TypeError("fetch failed"));
        const { getOIDCUserData } = await import("./auth");

        await expect(
            getOIDCUserData(
                { redirectURI: "http://localhost:5173/login/callback" },
                "test-code",
                "test-verifier",
                undefined,
                new URL("http://localhost:5173")
            )
        ).rejects.toSatisfy(
            (e: any) => e.name === "OAuthProviderError" && e.code === "OAUTH_PROVIDER_UNAVAILABLE"
        );
    });

    it("throws OAuthProviderError OAUTH_PROVIDER_ERROR on token exchange error", async () => {
        mockIssuerDiscover.mockResolvedValue({
            metadata: { id_token_signing_alg_values_supported: ["RS256"] },
            Client: class {
                callback = vi.fn().mockRejectedValue(new Error("invalid_grant"));
                userinfo = vi.fn();
            },
        });
        const { getOIDCUserData } = await import("./auth");

        await expect(
            getOIDCUserData(
                { redirectURI: "http://localhost:5173/login/callback" },
                "test-code",
                "test-verifier",
                undefined,
                new URL("http://localhost:5173")
            )
        ).rejects.toSatisfy(
            (e: any) => e.name === "OAuthProviderError" && e.code === "OAUTH_PROVIDER_ERROR"
        );
    });
});
