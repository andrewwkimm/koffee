// @vitest-environment node
import config from "../vite.config";

describe("vite dev server config", () => {
  it("sets Cross-Origin-Opener-Policy to same-origin", () => {
    expect(config.server?.headers?.["Cross-Origin-Opener-Policy"]).toBe("same-origin");
  });

  it("sets Cross-Origin-Embedder-Policy to require-corp", () => {
    expect(config.server?.headers?.["Cross-Origin-Embedder-Policy"]).toBe("require-corp");
  });
});