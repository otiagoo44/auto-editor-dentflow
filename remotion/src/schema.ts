import {z} from 'zod';

const localPath = z.string().regex(/^jobs\/job_[a-zA-Z0-9_-]+\/[a-zA-Z0-9_.-]+$/);
const cleanText = (length: number) => z.string().max(length).refine(t => !/[\x00-\x08\x0b-\x1f]/.test(t));
export const paramsSchema = z.object({
  title: cleanText(86).optional(), subtitle: cleanText(130).optional(),
  eyebrow: cleanText(40).optional(), cta: cleanText(54).optional(),
  theme: z.enum(['dark', 'light']),
  items: z.array(z.object({label: cleanText(40), value: cleanText(72), at_seconds: z.number().min(0).max(600)}).strict()).max(4),
}).strict();
export const sceneSchema = z.object({
  id: z.string().max(120),
  template: z.enum(['QuestionHook','AnimatedMessages','CRMHighlight','StepDiagram','ScreenshotFocus','SummaryCTA']),
  kind: z.enum(['text','asset','motion','reframe']),
  start_frame: z.number().int().min(0), duration_frames: z.number().int().positive(),
  params: paramsSchema, layout: z.enum(['card','full']), demo: z.boolean(),
  animation: z.enum(['none','fade','HOOK_TEXT','CALLOUT','CAMERA_PUNCH_IN_OUT']),
  asset: z.object({path: localPath, video: z.boolean()}).strict().optional(),
  camera: z.object({scale: z.number().min(1).max(1.3), x: z.number().min(0).max(1), y: z.number().min(0).max(1), animated: z.boolean()}).strict().optional(),
}).strict();
export const propsSchema = z.object({
  format_version: z.literal(1), job_id: z.string().regex(/^job_[a-zA-Z0-9_-]+$/),
  template: z.enum(['educativo','comercial']), fps: z.number().int().min(1).max(60),
  width: z.number().int().min(180).max(2160), height: z.number().int().min(320).max(3840),
  duration_frames: z.number().int().positive().max(36000), base_video: localPath.nullable(),
  scenes: z.array(sceneSchema).max(200),
  captions: z.array(z.object({text: cleanText(200), startMs: z.number().min(0), endMs: z.number().positive(),
    timestampMs: z.null(), confidence: z.null()}).strict()).max(10000),
  subtitle_style: z.object({font_size:z.number().min(32).max(72),margin_v:z.number().min(180).max(600)}).strict(),
  speech_windows:z.array(z.tuple([z.number().min(0),z.number().min(0)])).max(20000),
  music: z.object({path:localPath,volume:z.number().min(0).max(.3),ducking:z.number().min(0).max(1)}).strict().nullable(),
  metadata:z.object({source_sha256:z.string(),source_type:z.string()}).strict(),
}).strict().superRefine((p,ctx)=>{
  const endMs=p.duration_frames/p.fps*1000;
  if(Math.abs(p.width/p.height-9/16)>.001) ctx.addIssue({code:'custom',message:'Formato vertical 9:16 requerido.'});
  let end=0;
  for(const s of p.scenes){
    if(s.start_frame<end || s.start_frame+s.duration_frames>p.duration_frames) ctx.addIssue({code:'custom',message:'Escena fuera de timeline o solapada.'});
    end=s.start_frame+s.duration_frames;
    if(s.kind==='asset'&&!s.asset) ctx.addIssue({code:'custom',message:'Asset faltante.'});
    if(s.kind==='reframe'&&!s.camera) ctx.addIssue({code:'custom',message:'Cámara faltante.'});
    if(s.params.items.some(i=>i.at_seconds*p.fps>=s.duration_frames)) ctx.addIssue({code:'custom',message:'Item fuera de escena.'});
  }
  for(const c of p.captions) if(c.endMs<=c.startMs||c.endMs>endMs+34||c.text.split('\n').length>2) ctx.addIssue({code:'custom',message:'Caption fuera de timeline o de dos líneas.'});
  const paths=[p.base_video,p.music?.path,...p.scenes.map(s=>s.asset?.path)].filter(Boolean);
  for(const path of paths) if(!path!.startsWith(`jobs/${p.job_id}/`)) ctx.addIssue({code:'custom',message:'Asset fuera del job.'});
});
export type Props = z.infer<typeof propsSchema>;
export type Scene = z.infer<typeof sceneSchema>;
export type Params = z.infer<typeof paramsSchema>;
