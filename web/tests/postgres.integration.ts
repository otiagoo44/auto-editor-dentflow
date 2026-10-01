import test from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { db, one } from "../lib/db";
import { createJob, lease } from "../lib/jobs";
import { contents } from "../lib/content";
test(
  "PostgreSQL migration and mutually exclusive worker lease",
  { skip: !process.env.DATABASE_URL },
  async () => {
    process.env.STUDIO_MODE = "REMOTE_STUDIO";
    await contents();
    const key = randomUUID();
    const a = await createJob(
      "DEMO-TECNICA",
      { source_mode: "graphics", engine: "remotion" },
      key,
    );
    const b = await createJob(
      "DEMO-TECNICA",
      { source_mode: "graphics", engine: "remotion" },
      key,
    );
    assert.equal(a.id, b.id);
    const results = await Promise.all([
      lease("pg-test-a", {}),
      lease("pg-test-b", {}),
    ]);
    assert.equal(results.filter(Boolean).length, 1);
    await db(
      "UPDATE jobs SET status='canceled',lease_hash=NULL,lease_until=NULL WHERE id=$1",
      [a.id],
    );
    assert.equal(
      (await one("SELECT status FROM jobs WHERE id=$1", [a.id]))?.status,
      "canceled",
    );
  },
);
