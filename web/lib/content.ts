import { randomUUID } from "node:crypto";
import { db, one, unpack } from "./db";
import { contentSchema, Content } from "./contracts";
import { owner, now } from "./config";
import { check, hash } from "./security";

export const demo: Content = contentSchema.parse({
  id: "DEMO-TECNICA",
  title: "Probá tu primer montaje",
  source_version: "demo-tecnica-1",
  script:
    "Demo técnica independiente del contenido V3. Subí una grabación o probá la composición sin cámara.",
  visual_plan:
    "Una pregunta de apertura, una idea clara y una acción final. Los gráficos de esta demo son ilustrativos.",
  scenes: [
    {
      id: "hook",
      match_text: "",
      purpose: "Probar el recorrido de render",
      reason: "Demo técnica explícita",
      template: "QuestionHook",
      params: { title: "Cada consulta. Un siguiente paso." },
      approved: true,
      source_time: [0, 4],
      layout: "full",
      demo: true,
    },
    {
      id: "cta",
      match_text: "",
      purpose: "Cerrar la demo",
      reason: "Demo técnica explícita",
      template: "SummaryCTA",
      params: { title: "Una idea clara", cta: "Revisá el siguiente paso" },
      approved: true,
      source_time: [4, 8],
      layout: "full",
      demo: true,
    },
  ],
});

export async function ensureDemo() {
  await db(
    "INSERT INTO content_items (id,owner_id,source_version,data) VALUES ($1,$2,$3,$4) ON CONFLICT(id) DO NOTHING",
    [demo.id, owner, demo.source_version, JSON.stringify(demo)],
  );
}
export async function contents() {
  await ensureDemo();
  return (
    await db("SELECT * FROM content_items WHERE owner_id=$1 ORDER BY id", [
      owner,
    ])
  ).map((r) => unpack<Content>(r));
}
export async function getContent(identity: string) {
  await ensureDemo();
  const row = await one(
    "SELECT * FROM content_items WHERE id=$1 AND owner_id=$2",
    [identity, owner],
  );
  check(row, 404, "Contenido no encontrado.");
  return unpack<Content>(row);
}
export async function saveContent(content: Content) {
  const old = await getContent(content.id);
  await db(
    "INSERT INTO content_versions (id,content_id,owner_id,created_at,data) VALUES ($1,$2,$3,$4,$5)",
    [randomUUID(), content.id, owner, now(), JSON.stringify(old)],
  );
  const value = {
    ...content,
    original: old.original ?? old,
    source_version: old.source_version,
  };
  await db("UPDATE content_items SET data=$1 WHERE id=$2 AND owner_id=$3", [
    JSON.stringify(value),
    content.id,
    owner,
  ]);
  return value;
}
// Unknown source shapes are rejected with an actionable message; scripts are never inferred.
export async function importContent(input: unknown) {
  const document = input as { source_version?: string; items?: unknown[] };
  const items = Array.isArray(input) ? input : document?.items;
  check(
    Array.isArray(items) && items.length > 0 && items.length <= 100,
    400,
    "El seed debe contener items; conservar el archivo original para adaptar su formato.",
  );
  const version =
    document.source_version ||
    "import-" + hash(JSON.stringify(input)).slice(0, 12);
  const parsed = items.map((raw) => {
    const x = raw as Record<string, unknown>;
    return contentSchema.parse({
      ...x,
      source_version: x.source_version || version,
      original: raw,
    });
  });
  check(
    new Set(parsed.map((x) => x.id)).size === parsed.length,
    400,
    "El seed contiene códigos duplicados.",
  );
  let imported = 0;
  for (const c of parsed) {
    const result = await db(
      "INSERT INTO content_items (id,owner_id,source_version,data) VALUES ($1,$2,$3,$4) ON CONFLICT(id) DO NOTHING RETURNING id",
      [c.id, owner, c.source_version, JSON.stringify(c)],
    );
    imported += result.length;
  }
  return { imported, unchanged: parsed.length - imported };
}
