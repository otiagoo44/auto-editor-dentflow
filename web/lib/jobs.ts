import { randomUUID, randomBytes } from "node:crypto";
import { db, one, unpack, transaction } from "./db";
import { owner, now } from "./config";
import { Asset, JobData, Output, Settings, settingsSchema } from "./contracts";
import { check, hash, mediaLink } from "./security";
import { getContent } from "./content";

export async function rateLimit(key: string, limit: number, ms: number) {
  const stamp = Math.floor(now() / ms) * ms;
  const rows = await db(
    "INSERT INTO rate_limits (id,window_start,count) VALUES ($1,$2,1) ON CONFLICT(id) DO UPDATE SET count=CASE WHEN rate_limits.window_start=$2 THEN rate_limits.count+1 ELSE 1 END,window_start=$2 RETURNING count",
    [key, stamp],
  );
  check(
    Number(rows[0].count) <= limit,
    429,
    "Límite temporal alcanzado. Intentá más tarde.",
  );
}
export async function asset(identity: string) {
  const row = await one(
    "SELECT * FROM assets WHERE id=$1 AND owner_id=$2 AND status=$3",
    [identity, owner, "ready"],
  );
  check(row, 404, "Archivo no disponible.");
  return unpack<Asset>(row);
}
export async function job(identity: string) {
  const row = await one("SELECT * FROM jobs WHERE id=$1 AND owner_id=$2", [
    identity,
    owner,
  ]);
  check(row, 404, "Trabajo no encontrado.");
  return row;
}
export async function event(identity: string, phase: string) {
  await db(
    "INSERT INTO job_events (id,job_id,created_at,phase) VALUES ($1,$2,$3,$4)",
    [randomUUID(), identity, now(), phase],
  );
}
export async function createJob(
  contentId: string,
  input: unknown,
  intentKey: string,
  projectId?: string,
) {
  check(/^[\w-]{8,100}$/.test(intentKey), 400, "Falta clave de idempotencia.");
  const settings = settingsSchema.parse(input);
  const content = await getContent(contentId);
  if (content.demo_gate && !content.demo_approved)
    settings.scenes = settings.scenes.map((s) => ({ ...s, approved: false }));
  const settingsHash = hash(JSON.stringify({ content, settings }));
  const existing = await one(
    "SELECT * FROM jobs WHERE owner_id=$1 AND intent_key=$2",
    [owner, intentKey],
  );
  if (existing) {
    check(
      existing.settings_hash === settingsHash,
      409,
      "La clave ya pertenece a otras opciones.",
    );
    return existing;
  }
  await rateLimit(
    "renders:" + owner,
    Number(process.env.MAX_RENDERS_PER_DAY || 50),
    86400000,
  );
  if (settings.asset_id) {
    const a = await asset(settings.asset_id);
    check(a.mime.startsWith("video/"), 400, "La fuente debe ser un video.");
    if (settings.source_sha256 && a.sha256)
      check(settings.source_sha256 === a.sha256, 409, "Cambió la grabación.");
  }
  for (const s of settings.scenes)
    if (s.asset_id) {
      const a = await asset(s.asset_id);
      check(
        a.approved && a.rights,
        400,
        "El recurso necesita aprobación y procedencia.",
      );
    }
  if (settings.music_asset_id) {
    const a = await asset(settings.music_asset_id);
    check(
      a.mime.startsWith("audio/") && a.approved && a.rights,
      400,
      "La música requiere derechos declarados.",
    );
    check(settings.engine === "remotion", 400, "Música requiere Remotion.");
  }
  if (settings.parent_job_id) {
    const parent = await job(settings.parent_job_id);
    check(
      !projectId || projectId === parent.project_id,
      400,
      "Proyecto inválido.",
    );
    projectId = String(parent.project_id);
  }
  if (projectId) {
    const project = await one(
      "SELECT * FROM projects WHERE id=$1 AND owner_id=$2",
      [projectId, owner],
    );
    check(project, 404, "Proyecto no encontrado.");
    check(
      !unpack<{ deleting?: boolean }>(project).deleting,
      409,
      "El proyecto se está borrando.",
    );
  } else {
    projectId = randomUUID();
    await db(
      "INSERT INTO projects (id,owner_id,content_id,created_at,data) VALUES ($1,$2,$3,$4,$5)",
      [
        projectId,
        owner,
        contentId,
        now(),
        JSON.stringify({
          title: content.title,
          source_mode: settings.source_mode,
        }),
      ],
    );
  }
  const identity = randomUUID(),
    stamp = now();
  const data: JobData = { settings, content };
  await transaction(async () => {
    const project = await one(
      "UPDATE projects SET data=data WHERE id=$1 AND owner_id=$2 RETURNING *",
      [projectId, owner],
    );
    check(
      project && !unpack<{ deleting?: boolean }>(project).deleting,
      409,
      "El proyecto ya se está borrando.",
    );
    const references = [
      ...new Set(
        [
          settings.asset_id,
          settings.music_asset_id,
          ...settings.scenes.map((s) => s.asset_id),
        ].filter(Boolean),
      ),
    ].sort();
    for (const reference of references) {
      const locked = await one(
        "UPDATE assets SET status=status WHERE id=$1 AND owner_id=$2 AND status='ready' RETURNING id",
        [reference, owner],
      );
      check(locked, 409, "Un recurso ya no está disponible.");
    }
    await db(
      "INSERT INTO jobs (id,owner_id,project_id,status,created_at,updated_at,intent_key,settings_hash,data) VALUES ($1,$2,$3,$4,$5,$5,$6,$7,$8) ON CONFLICT(owner_id,intent_key) DO NOTHING",
      [
        identity,
        owner,
        projectId,
        "queued",
        stamp,
        intentKey,
        settingsHash,
        JSON.stringify(data),
      ],
    );
  });
  const result = await one(
    "SELECT * FROM jobs WHERE owner_id=$1 AND intent_key=$2",
    [owner, intentKey],
  );
  check(result, 500, "No se pudo crear el trabajo.");
  check(
    result.settings_hash === settingsHash,
    409,
    "Conflicto de idempotencia.",
  );
  await event(String(result.id), "queued");
  return result;
}
export async function publicJob(row: Record<string, unknown>) {
  const data = unpack<JobData>(row);
  const outputs = (
    await db("SELECT * FROM outputs WHERE job_id=$1 AND owner_id=$2", [
      row.id,
      owner,
    ])
  ).map((r) => {
    const o = unpack<Output>(r);
    const { key, ...publicOutput } = o;
    return { ...publicOutput, url: mediaLink(o.id) };
  });
  return {
    id: row.id,
    project_id: row.project_id,
    status: row.status,
    created_at: row.created_at,
    attempt: row.attempt,
    ...data,
    outputs: ["preview_ready", "final_ready"].includes(String(row.status))
      ? outputs
      : [],
    events: await db(
      "SELECT created_at,phase FROM job_events WHERE job_id=$1 ORDER BY created_at",
      [row.id],
    ),
  };
}
export async function lease(
  workerId: string,
  capabilities: Record<string, unknown>,
) {
  await db(
    "INSERT INTO workers (id,last_seen,data) VALUES ($1,$2,$3) ON CONFLICT(id) DO UPDATE SET last_seen=$2,data=$3",
    [workerId, now(), JSON.stringify(capabilities)],
  );
  // Expired workers lose their lease. A stale attempt cannot write progress or finish.
  await db(
    "UPDATE jobs SET status=CASE WHEN status='cancel_requested' THEN 'canceled' WHEN attempt>=3 THEN 'failed' ELSE 'queued' END,lease_hash=NULL,lease_until=NULL,worker_id=NULL WHERE lease_until<$1",
    [now()],
  );
  const token = randomBytes(32).toString("hex");
  const rows = await db(
    "UPDATE jobs SET status='leased',lease_hash=$1,lease_until=$2,worker_id=$3,attempt=attempt+1,updated_at=$4 WHERE id=(SELECT id FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1) AND status='queued' AND NOT EXISTS (SELECT 1 FROM jobs WHERE lease_until>$4) RETURNING *",
    [hash(token), now() + 120000, workerId, now()],
  );
  if (!rows.length) return null;
  const row = rows[0];
  await event(String(row.id), "leased");
  const data = unpack<JobData>(row);
  const ids = new Set(
    [
      data.settings.asset_id,
      data.settings.music_asset_id,
      ...data.settings.scenes.map((s) => s.asset_id),
    ].filter(Boolean) as string[],
  );
  const assets = await Promise.all([...ids].map(asset));
  return {
    id: row.id,
    attempt: row.attempt,
    lease_token: token,
    ...data,
    assets: assets.map(({ key, ...a }) => a),
  };
}
export async function requireLease(identity: string, token: string) {
  const row = await job(identity);
  check(
    row.lease_hash === hash(token) && Number(row.lease_until) > now(),
    409,
    "Lease vencido o reemplazado.",
  );
  return row;
}
export async function changeLease(
  identity: string,
  token: string,
  phase: string,
  data?: JobData,
) {
  const rows = await db(
    "UPDATE jobs SET status=$1,updated_at=$2,lease_until=$3,data=COALESCE($4,data) WHERE id=$5 AND lease_hash=$6 AND lease_until>$2 AND status<>$7 RETURNING id",
    [
      phase,
      now(),
      now() + 120000,
      data ? JSON.stringify(data) : null,
      identity,
      hash(token),
      "cancel_requested",
    ],
  );
  check(rows.length, 409, "Lease vencido o cancelación solicitada.");
  await event(identity, phase);
}
