import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { randomUUID } from "node:crypto";
process.env.STUDIO_DATA_DIR = mkdtempSync(
  path.join(os.tmpdir(), "dentflow-db-test-"),
);
import {
  createJob,
  lease,
  requireLease,
  publicJob,
  changeLease,
  rateLimit,
} from "../lib/jobs";
import { db, one } from "../lib/db";
import {
  contents,
  importContent,
  saveContent,
  getContent,
} from "../lib/content";
import { GET, POST, PUT, PATCH } from "../app/api/[...path]/route";

test("idempotent content import preserves original and saves edited versions", async () => {
  const c = {
    id: "TEST-ONLY",
    title: "Fixture técnico",
    source_version: "test-only",
    script: "Texto literal con tildes.",
  };
  assert.equal((await importContent({ items: [c] })).imported, 1);
  assert.equal(
    (await importContent({ items: [{ ...c, script: "No reemplazar" }] }))
      .imported,
    0,
  );
  assert.equal((await getContent(c.id)).script, c.script);
  await saveContent({ ...(await getContent(c.id)), script: "Versión editada" });
  assert.equal(
    ((await getContent(c.id)).original as typeof c).script,
    c.script,
  );
  assert.equal((await db("SELECT * FROM content_versions")).length, 1);
  assert((await contents()).some((x) => x.id === "DEMO-TECNICA"));
});
test("double click, one lease, expiration, stale worker and cancellation", async () => {
  const key = randomUUID(),
    settings = { source_mode: "graphics", engine: "remotion", kind: "preview" };
  const first = await createJob("DEMO-TECNICA", settings, key);
  const same = await createJob("DEMO-TECNICA", settings, key);
  assert.equal(first.id, same.id);
  await assert.rejects(
    createJob("DEMO-TECNICA", { ...settings, duration: 9 }, key),
    /clave/,
  );
  const [a, b] = await Promise.all([lease("pc-a", {}), lease("pc-b", {})]);
  const held = a || b;
  assert(held);
  assert.equal([a, b].filter(Boolean).length, 1);
  await requireLease(String(first.id), held.lease_token);
  await assert.rejects(requireLease(String(first.id), "wrong"), /Lease/);
  await db("UPDATE jobs SET lease_until=$1 WHERE id=$2", [
    Date.now() - 1,
    first.id,
  ]);
  const renewed = await lease("pc-b", {});
  assert(renewed);
  assert.equal(renewed.attempt, 2);
  await assert.rejects(
    requireLease(String(first.id), held.lease_token),
    /Lease/,
  );
  await db("UPDATE jobs SET status='cancel_requested' WHERE id=$1", [first.id]);
  await assert.rejects(
    changeLease(String(first.id), renewed.lease_token, "rendering"),
    /cancelación/,
  );
  await db("UPDATE jobs SET lease_until=$1 WHERE id=$2", [
    Date.now() - 1,
    first.id,
  ]);
  await lease("pc-c", {});
  assert.equal(
    (await one("SELECT status FROM jobs WHERE id=$1", [first.id]))?.status,
    "canceled",
  );
  const pub = await publicJob(first);
  assert(!("lease_hash" in pub));
  assert(!("lease_token" in pub));
});
test("quota counter is persisted and enforced", async () => {
  await rateLimit("test", 1, 60000);
  await assert.rejects(rateLimit("test", 1, 60000), /Límite/);
});
test("API denies unauthorized worker and checks file type and upload identity", async () => {
  const req = (url: string, body: unknown) =>
    new Request("http://localhost:3000/api/" + url, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Content-Type": "application/json" },
    });
  assert.equal(
    (await POST(req("worker/lease", { worker_id: "evil" }))).status,
    401,
  );
  assert.equal(
    (await POST(req("assets", { name: "x.exe", mime: "video/mp4", size: 10 })))
      .status,
    400,
  );
  const upload = await POST(
    req("assets", { name: "fixture.mp4", mime: "video/mp4", size: 16 }),
  );
  assert.equal(upload.status, 201);
  const { id } = await upload.json();
  const put = new Request(`http://localhost:3000/api/assets/${id}/file`, {
    method: "PUT",
    body: Buffer.alloc(16),
  });
  assert.equal((await PUT(put)).status, 200);
  const repeat = new Request(`http://localhost:3000/api/assets/${id}/file`, {
    method: "PUT",
    body: Buffer.alloc(16),
  });
  assert.equal((await PUT(repeat)).status, 404);
  const missing = await GET(
    new Request(`http://localhost:3000/api/outputs/${randomUUID()}`),
  );
  assert.equal(missing.status, 403);
  const crossing = new Request(
    `http://localhost:3000/api/content/DEMO-TECNICA`,
    { method: "PATCH", body: "{}", headers: { Origin: "https://evil.test" } },
  );
  assert.equal((await PATCH(crossing)).status, 403);
});
