import { describe, it, expect, beforeEach } from "vitest";
import {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
  isTokenExpiringSoon,
} from "../api";

describe("Token helpers", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("getAccessToken returns null when no token", () => {
    expect(getAccessToken()).toBeNull();
  });

  it("setTokens stores access and refresh tokens", () => {
    setTokens("access123", "refresh456");
    expect(getAccessToken()).toBe("access123");
    expect(getRefreshToken()).toBe("refresh456");
  });

  it("setTokens stores only access token when refresh is omitted", () => {
    setTokens("access_only");
    expect(getAccessToken()).toBe("access_only");
    expect(getRefreshToken()).toBeNull();
  });

  it("clearTokens removes both tokens", () => {
    setTokens("a", "r");
    clearTokens();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("isTokenExpiringSoon returns true when no token", () => {
    expect(isTokenExpiringSoon()).toBe(true);
  });

  it("isTokenExpiringSoon returns true for invalid token", () => {
    setTokens("not-a-jwt");
    expect(isTokenExpiringSoon()).toBe(true);
  });

  it("isTokenExpiringSoon returns false for valid far-future token", () => {
    // Create a minimal JWT with exp far in the future
    const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
    const payload = btoa(
      JSON.stringify({ sub: "user", exp: Math.floor(Date.now() / 1000) + 3600, type: "access" })
    );
    const fakeJwt = `${header}.${payload}.fakesig`;
    setTokens(fakeJwt);
    expect(isTokenExpiringSoon(120)).toBe(false);
  });

  it("isTokenExpiringSoon returns true for nearly-expired token", () => {
    const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
    const payload = btoa(
      JSON.stringify({ sub: "user", exp: Math.floor(Date.now() / 1000) + 30, type: "access" })
    );
    const fakeJwt = `${header}.${payload}.fakesig`;
    setTokens(fakeJwt);
    // Token expires in 30s, buffer is 120s → should be expiring soon
    expect(isTokenExpiringSoon(120)).toBe(true);
  });
});
