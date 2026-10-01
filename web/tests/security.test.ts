import test from "node:test";
import assert from "node:assert/strict";
import { authorize, hash, mediaLink, verifyMediaLink } from "../lib/security";
import { localPath } from "../lib/storage";
import { settingsSchema } from "../lib/contracts";

test("local access rejects remote hosts, cross-site writes and cloud misconfiguration", () => {
  delete process.env.STUDIO_MODE;
  delete process.env.VERCEL;
  authorize(new Request("http://127.0.0.1:3000/api/content"));
  assert.throws(
    () => authorize(new Request("http://evil.test/api/content")),
    /loopback/,
  );
  assert.throws(
    () =>
      authorize(
        new Request("http://localhost:3000/api/jobs", {
          method: "POST",
          headers: { Origin: "https://evil.test" },
        }),
      ),
    /Origen/,
  );
  process.env.VERCEL = "1";
  assert.throws(
    () => authorize(new Request("http://localhost:3000/")),
    /REMOTE_STUDIO/,
  );
  delete process.env.VERCEL;
});
test("remote owner and worker identities cannot impersonate each other", () => {
  process.env.STUDIO_MODE = "REMOTE_STUDIO";
  process.env.OWNER_PASSWORD = "owner-test-secret-that-is-long-enough";
  process.env.WORKER_TOKEN = "worker-test-secret-that-is-long-enough";
  const bearer = { Authorization: "Bearer " + process.env.WORKER_TOKEN };
  assert.throws(
    () =>
      authorize(
        new Request("https://studio.test/api/jobs", { headers: bearer }),
      ),
    /propietario/,
  );
  authorize(
    new Request("https://studio.test/api/worker/lease", { headers: bearer }),
    true,
  );
  assert.throws(
    () => authorize(new Request("https://studio.test/api/worker/lease"), true),
    /autorizado/,
  );
  authorize(
    new Request("https://studio.test/", {
      headers: {
        Authorization:
          "Basic " +
          Buffer.from("owner:" + process.env.OWNER_PASSWORD).toString("base64"),
      },
    }),
  );
  delete process.env.STUDIO_MODE;
  delete process.env.OWNER_PASSWORD;
  delete process.env.WORKER_TOKEN;
});
test("paths and settings fail closed; no caller paths, source URLs or executable code", () => {
  for (const key of [
    "../x",
    "inputs/../../secret",
    "C:/Windows/test",
    "outputs/a/foo.mp4",
    "https://example.com/x",
  ])
    assert.throws(() => localPath(key));
  assert.equal(hash("test").length, 64);
  assert.throws(() => settingsSchema.parse({ source_mode: "recording" }));
  assert.throws(() =>
    settingsSchema.parse({ source_mode: "graphics", engine: "ffmpeg" }),
  );
  assert.throws(() =>
    settingsSchema.parse({
      source_mode: "graphics",
      engine: "remotion",
      source: "C:/raw.mp4",
    }),
  );
});
test("signed media URLs expire and cannot be replayed for another output", () => {
  const link = new URL(mediaLink("fixture"), "http://localhost");
  verifyMediaLink(link, "fixture");
  assert.throws(() => verifyMediaLink(link, "other"), /Firma/);
  assert.throws(
    () =>
      verifyMediaLink(
        new URL(mediaLink("fixture", Date.now() - 1), "http://localhost"),
        "fixture",
      ),
    /vencido/,
  );
});
