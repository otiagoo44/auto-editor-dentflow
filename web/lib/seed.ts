import { z } from "zod";
import { Content, contentSchema } from "./contracts";

const sourceItem = z
  .object({
    code: z.string().regex(/^(R\d{2}|A[1-3])$/),
    title: z.string(),
    week: z.number().nullable(),
    script: z.string(),
    visual_plan: z.string(),
    caption: z.string(),
    cta: z.string(),
    fields: z.record(
      z.string(),
      z.object({ label: z.string(), text: z.string() }),
    ),
  })
  .passthrough();
const sourceDocument = z
  .object({
    source_document: z.string(),
    source_date: z.string(),
    demo_gates: z.record(
      z.string(),
      z.object({ reel: z.string(), title: z.string(), text: z.string() }),
    ),
    items: z.array(sourceItem).length(21),
  })
  .passthrough();

/** Explicit adapter for the user's original seed; no script rewriting. */
export function adaptV3(input: unknown): Content[] {
  const source = sourceDocument.parse(input);
  const expected = new Set([
    ...Array.from(
      { length: 18 },
      (_, i) => `R${String(i + 1).padStart(2, "0")}`,
    ),
    "A1",
    "A2",
    "A3",
  ]);
  for (const item of source.items) {
    if (!expected.delete(item.code))
      throw new Error("Código V3 duplicado o desconocido.");
  }
  if (expected.size) throw new Error("El seed V3 está incompleto.");
  return source.items.map((item) => {
    const hookText = item.fields.C.text.split(
      /  (?:Apertura de prueba|Selección inicial):/,
    )[0];
    const hooks = hookText
      .split(/(?:^|\s)[123]\)\s*/)
      .map((h) => h.trim())
      .filter(Boolean);
    if (hooks.length !== 3) throw new Error(`Revisar hooks de ${item.code}.`);
    const date = item.fields.A.text.match(/(\d{2})\/(\d{2})\/(\d{4})/);
    const gate = Object.entries(source.demo_gates).find(
      ([, g]) => g.reel === item.code,
    );
    return contentSchema.parse({
      id: item.code,
      title: item.title,
      week: item.week ?? 0,
      source_version: `V3-${source.source_date}`,
      script: item.script,
      hooks,
      caption: item.caption,
      cta: item.cta,
      visual_plan: item.visual_plan,
      date: date ? `${date[3]}-${date[2]}-${date[1]}` : "",
      demo_gate: gate ? `${gate[0]} · ${gate[1].title}\n${gate[1].text}` : "",
      demo_approved: false,
      original: {
        source_document: source.source_document,
        source_date: source.source_date,
        item,
      },
      scenes: [
        {
          id: `${item.code}-opening`,
          match_text: item.script
            .replace(/^«|»$/g, "")
            .split(/\s+/)
            .slice(0, 8)
            .join(" "),
          purpose: "Presentar la pregunta central del guion V3",
          reason:
            "Título original, asociado a una frase literal única; requiere aprobación editorial",
          template: "QuestionHook",
          params: { title: item.title },
          duration: 4,
          approved: false,
          demo: false,
          layout: "card",
        },
      ],
    });
  });
}
