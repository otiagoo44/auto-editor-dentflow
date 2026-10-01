import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, existsSync } from "node:fs";
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
import { db, one, transaction } from "../lib/db";
import {
  contents,
  importContent,
  saveContent,
  getContent,
} from "../lib/content";
import { GET, POST, PUT, PATCH } from "../app/api/[...path]/route";
import { saveLocal, localPath } from "../lib/storage";
import { deleteAsset, deleteProject } from "../lib/cleanup";
import { owner } from "../lib/config";

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

test("a failed transaction rolls back and never exposes partial output metadata", async () => {
  const key = randomUUID();
  await assert.rejects(
    transaction(async () => {
      await db(
        "INSERT INTO rate_limits (id,window_start,count) VALUES ($1,0,1)",
        [key],
      );
      throw new Error("simulated interruption");
    }),
    /interruption/,
  );
  assert.equal(
    await one("SELECT * FROM rate_limits WHERE id=$1", [key]),
    undefined,
  );
});

test("finish is atomic and replaying a lost completion response is idempotent", async () => {
  process.env.WORKER_TOKEN = "test-worker-private-secret-at-least-32-chars";
  const created = await createJob(
    "DEMO-TECNICA",
    { source_mode: "graphics" },
    randomUUID(),
  );
  const held = await lease("finish-test", {});
  assert(held && held.id === created.id);
  const bytes = Buffer.alloc(64);
  const stored = await saveLocal(
    `outputs/${held.id}/${held.attempt}_preview.mp4`,
    new Blob([bytes]).stream(),
  );
  const body = {
    ...stored,
    duration: 1,
    resolution: [360, 640],
    source_sha256: "a".repeat(64),
    validation: "probe+full_decode_passed",
    report: {
      words: [],
      captions: [],
      events: [],
      time_map: [],
      decisions: [],
      source_sha256: "a".repeat(64),
      source_duration: 1,
      warnings: [],
    },
  };
  const finish = () =>
    POST(
      new Request(`http://localhost:3000/api/worker/${held.id}/finish`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${process.env.WORKER_TOKEN}`,
          "X-Lease-Token": held.lease_token,
        },
        body: JSON.stringify(body),
      }),
    );
  await db(
    "CREATE TRIGGER fail_finish BEFORE INSERT ON editorial_plans BEGIN SELECT RAISE(ABORT, 'test failure'); END",
  );
  assert.equal((await finish()).status, 500);
  assert.equal(
    (await db("SELECT * FROM outputs WHERE job_id=$1", [held.id])).length,
    0,
  );
  assert.equal(
    (await one("SELECT status FROM jobs WHERE id=$1", [held.id]))?.status,
    "leased",
  );
  await db("DROP TRIGGER fail_finish");
  assert.equal((await finish()).status, 200);
  assert.equal((await finish()).status, 200);
  assert.equal(
    (await db("SELECT * FROM outputs WHERE job_id=$1", [held.id])).length,
    1,
  );
  assert.equal(
    (await db("SELECT * FROM editorial_plans WHERE job_id=$1", [held.id]))
      .length,
    1,
  );
  delete process.env.WORKER_TOKEN;
});

test("deletion waits for active work and preserves the raw file until explicit removal", async () => {
  const assetId = randomUUID();
  const inputKey = `inputs/${assetId}/source.mp4`;
  await saveLocal(inputKey, new Blob([Buffer.alloc(32)]).stream());
  await db(
    "INSERT INTO assets (id,owner_id,status,created_at,data) VALUES ($1,$2,'ready',$3,$4)",
    [assetId, owner, Date.now(), JSON.stringify({
      id: assetId, name: "raw.mp4", mime: "video/mp4", size: 32,
      key: inputKey, approved: false, rights: "", tags: [], demo: false,
      created_at: Date.now(),
    })],
  );
  const created = await createJob("DEMO-TECNICA", {
    source_mode: "recording", asset_id: assetId, engine: "ffmpeg",
  }, randomUUID());
  await assert.rejects(deleteAsset(assetId), /montaje/);
  await assert.rejects(deleteProject(String(created.project_id)), /trabajo activo/);
  const outputKey = `outputs/${created.id}/1_preview.mp4`;
  await saveLocal(outputKey, new Blob([Buffer.alloc(32)]).stream());
  await db("UPDATE jobs SET status='failed' WHERE id=$1", [created.id]);
  await db("INSERT INTO outputs (id,job_id,owner_id,kind,created_at,data) VALUES ($1,$2,$3,$4,$5,$6)", [
    randomUUID(), created.id, owner, "preview", Date.now(), JSON.stringify({key: outputKey}),
  ]);
  await deleteProject(String(created.project_id));
  assert.equal(existsSync(localPath(outputKey)), false);
  assert.equal(existsSync(localPath(inputKey)), true);
  assert.equal(await one("SELECT id FROM projects WHERE id=$1", [created.project_id]), undefined);
  await deleteAsset(assetId);
  assert.equal(existsSync(localPath(inputKey)), false);
  assert.equal(await one("SELECT id FROM assets WHERE id=$1", [assetId]), undefined);
});
