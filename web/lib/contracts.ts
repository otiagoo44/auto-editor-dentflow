import { z } from "zod";
export const id = z.string().uuid();
export const text = (max: number) =>
  z
    .string()
    .max(max)
    .refine((x) => !/[\x00-\x08\x0b-\x1f]/.test(x));
export const word = z
  .object({
    start: z.number().finite().min(0),
    end: z.number().finite().positive(),
    text: text(120).min(1),
  })
  .strict();
export const scene = z
  .object({
    id: text(80).min(1),
    match_text: text(400).default(""),
    purpose: text(300).min(1),
    reason: text(500).min(1),
    template: z
      .enum([
        "QuestionHook",
        "AnimatedMessages",
        "CRMHighlight",
        "StepDiagram",
        "ScreenshotFocus",
        "SummaryCTA",
      ])
      .optional(),
    asset_id: id.optional(),
    params: z
      .object({
        title: text(86).optional(),
        subtitle: text(130).optional(),
        cta: text(54).optional(),
        eyebrow: text(40).optional(),
        theme: z.enum(["dark", "light"]).default("dark"),
        items: z
          .array(
            z
              .object({
                label: text(40).min(1),
                value: text(72).default(""),
                at_seconds: z.number().min(0).max(600).default(0),
              })
              .strict(),
          )
          .max(4)
          .default([]),
      })
      .strict()
      .optional(),
    approved: z.boolean().default(false),
    demo: z.boolean().default(true),
    duration: z.number().min(0.5).max(60).default(4),
    source_time: z.tuple([z.number().min(0), z.number().positive()]).optional(),
    layout: z.enum(["card", "full"]).default("card"),
    focus_region: z
      .tuple([z.number(), z.number(), z.number(), z.number()])
      .optional(),
  })
  .strict();
export const contentSchema = z
  .object({
    id: text(80).min(1),
    title: text(160).min(1),
    week: z.number().int().min(0).max(52).default(0),
    source_version: text(80).min(1),
    script: text(30000).default(""),
    hooks: z.array(text(1000)).max(10).default([]),
    caption: text(10000).default(""),
    cta: text(1000).default(""),
    visual_plan: z.unknown().optional(),
    scenes: z.array(scene).max(100).default([]),
    demo_gate: text(8000).default(""),
    demo_approved: z.boolean().default(false),
    date: text(30).default(""),
    status: z
      .enum([
        "planned",
        "needs_recording",
        "uploaded",
        "processing",
        "review",
        "approved",
        "scheduled",
        "published",
      ])
      .default("planned"),
    original: z.unknown().optional(),
  })
  .strict();
export type Content = z.infer<typeof contentSchema>;
export const settingsSchema = z
  .object({
    engine: z.enum(["ffmpeg", "remotion"]).default("remotion"),
    source_mode: z.enum(["recording", "graphics"]).default("recording"),
    kind: z.enum(["preview", "final"]).default("preview"),
    asset_id: id.optional(),
    duration: z.number().min(0.5).max(600).default(8),
    scenes: z.array(scene).max(100).default([]),
    words: z.array(word).max(15000).optional(),
    source_sha256: z
      .string()
      .regex(/^[a-f0-9]{64}$/)
      .optional(),
    music_asset_id: id.optional(),
    music_volume: z.number().min(0).max(0.3).default(0.1),
    preserve_pauses: z.boolean().default(true),
    parent_job_id: id.optional(),
  })
  .strict()
  .superRefine((s, c) => {
    if (s.source_mode === "recording" && !s.asset_id)
      c.addIssue({ code: "custom", message: "Primero subí una grabación." });
    if (s.source_mode === "graphics" && (s.engine !== "remotion" || s.asset_id))
      c.addIssue({
        code: "custom",
        message: "Gráficos requiere Remotion sin grabación.",
      });
    if (s.words && !s.source_sha256)
      c.addIssue({
        code: "custom",
        message: "Correcciones requieren SHA de la fuente.",
      });
  });
export type Settings = z.infer<typeof settingsSchema>;
export type Asset = {
  id: string;
  status?: "ready" | "deleting";
  name: string;
  mime: string;
  size: number;
  key: string;
  sha256?: string;
  duration?: number;
  approved: boolean;
  rights: string;
  tags: string[];
  demo: boolean;
  created_at: number;
};
export type JobData = {
  settings: Settings;
  content: Content;
  warnings?: string[];
  report?: Report;
  error?: string;
  reviewed?: boolean;
};
export type Report = {
  words: z.infer<typeof word>[];
  captions: { start: number; end: number; text: string }[];
  events: Record<string, unknown>[];
  time_map: Record<string, number>[];
  decisions: Record<string, unknown>[];
  source_sha256: string;
  source_duration: number;
  warnings: string[];
};
export type Output = {
  id: string;
  kind: "preview" | "final";
  key: string;
  sha256: string;
  size: number;
  duration: number;
  resolution: number[];
  source_sha256: string;
  validation: string;
};
export const phases = [
  "leased",
  "downloading",
  "probing",
  "transcribing",
  "planning",
  "cutting",
  "rendering",
  "qa",
  "uploading",
  "preview_ready",
  "final_ready",
] as const;
