import test from "node:test";
import assert from "node:assert/strict";
import original from "../data/seed-v3.json";
import { adaptV3 } from "../lib/seed";

test("original V3 seed preserves all 21 scripts, hooks, captions, dates and product gates", () => {
  const items = adaptV3(original);
  assert.equal(items.length, 21);
  assert.deepEqual(
    items.filter((i) => i.demo_gate).map((i) => i.id),
    ["R03", "R08", "R11", "R15"],
  );
  for (const item of items) {
    const source = original.items.find((s) => s.code === item.id)!;
    assert.equal(item.script, source.script);
    assert.equal(item.caption, source.caption);
    assert.equal(item.visual_plan, source.visual_plan);
    assert.equal(item.cta, source.cta);
    assert.equal(item.hooks.length, 3);
    assert.equal(item.demo_approved, false);
    assert(item.scenes.every((s) => !s.approved));
  }
  assert.equal(items[0].date, "2026-10-05");
  assert.equal(items[17].date, "2026-11-13");
  assert(items.slice(18).every((i) => !i.date));
  assert.throws(() => adaptV3({ ...original, items: original.items.slice(1) }));
  assert.throws(() =>
    adaptV3({
      ...original,
      items: original.items.map(() => original.items[0]),
    }),
  );
});
