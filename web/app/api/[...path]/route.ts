import { randomUUID } from "node:crypto";
import { z, ZodError } from "zod";
import { db, one, unpack, transaction } from "@/lib/db";
import { owner, now, remote, maxBytes, maxDuration } from "@/lib/config";
import {
  authorize,
  check,
  HttpError,
  jsonBody,
  hash,
  verifyMediaLink,
} from "@/lib/security";
import {
  Content,
  contentSchema,
  Asset,
  JobData,
  Output,
  id,
  phases,
  word,
} from "@/lib/contracts";
import {
  contents,
  getContent,
  saveContent,
  importContent,
} from "@/lib/content";
import {
  asset,
  job,
  createJob,
  publicJob,
  lease,
  requireLease,
  changeLease,
  event,
  rateLimit,
} from "@/lib/jobs";
import { saveLocal, streamFile, uploadToken, info } from "@/lib/storage";
import {
  deleteProject,
  deleteAsset,
  cleanupAbandonedUploads,
} from "@/lib/cleanup";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const response = (body: unknown, status = 200) =>
  Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
const mimeExtensions: Record<string, string[]> = {
  "video/mp4": ["mp4", "m4v"],
  "video/quicktime": ["mov"],
  "video/webm": ["webm"],
  "image/png": ["png"],
  "image/jpeg": ["jpg", "jpeg"],
  "image/webp": ["webp"],
  "audio/mpeg": ["mp3"],
  "audio/wav": ["wav"],
  "audio/x-wav": ["wav"],
  "audio/mp4": ["m4a"],
  "audio/ogg": ["ogg"],
};

async function dispatch(req: Request) {
  const url = new URL(req.url),
    p = url.pathname.split("/").filter(Boolean).slice(1),
    method = req.method;
  authorize(req, p[0] === "worker");
  if (p[0] === "status" && method === "GET") {
    const workers = await db(
      "SELECT id,last_seen,data FROM workers ORDER BY last_seen DESC",
    );
    return response({
      mode: remote() ? "REMOTE_STUDIO" : "LOCAL_STUDIO",
      app_name: process.env.APP_DISPLAY_NAME || "DentFlow Studio",
      max_bytes: maxBytes(),
      max_duration: maxDuration(),
      worker_online: workers.some((w) => now() - Number(w.last_seen) < 45000),
      workers: workers.map((w) => ({
        id: w.id,
        online: now() - Number(w.last_seen) < 45000,
        capabilities: unpack(w),
      })),
      seed_loaded: (await contents()).some((c) => c.id === "R01"),
    });
  }
  if (p[0] === "content") {
    if (method === "GET" && !p[1]) return response(await contents());
    if (method === "POST" && p[1] === "import")
      return response(await importContent(await jsonBody(req)));
    if (method === "POST" && !p[1]) {
      const body = await jsonBody(req);
      const c = contentSchema.parse({
        ...body,
        id: "EXTRA-" + randomUUID(),
        source_version: "owner",
      });
      await db(
        "INSERT INTO content_items (id,owner_id,source_version,data) VALUES ($1,$2,$3,$4)",
        [c.id, owner, c.source_version, JSON.stringify(c)],
      );
      return response(c, 201);
    }
    if (method === "GET" && p[1])
      return response(await getContent(decodeURIComponent(p[1])));
    if (method === "PATCH" && p[1]) {
      const old = await getContent(decodeURIComponent(p[1]));
      const b = await jsonBody(req);
      check(
        !("original" in b) && !("source_version" in b) && !("id" in b),
        400,
        "La fuente original es inmutable.",
      );
      return response(await saveContent(contentSchema.parse({ ...old, ...b })));
    }
  }
  if (p[0] === "assets") {
    if (method === "DELETE" && p[1]) {
      id.parse(p[1]);
      await deleteAsset(p[1]);
      return response({ ok: true });
    }
    if (method === "GET" && !p[1])
      return response(
        (
          await db(
            "SELECT * FROM assets WHERE owner_id=$1 AND status IN ('ready','deleting') ORDER BY created_at DESC",
            [owner],
          )
        ).map((r) => {
          const { key, ...a } = unpack<Asset>(r);
          return { ...a, status: r.status };
        }),
      );
    if (method === "POST" && !p[1]) {
      await rateLimit("uploads:" + owner, 50, 3600000);
      const b = z
        .object({
          name: z.string().min(1).max(180),
          mime: z.string(),
          size: z.number().int().positive(),
          rights: z.string().max(2000).default(""),
          approved: z.boolean().default(false),
          tags: z.array(z.string().max(80)).max(20).default([]),
          demo: z.boolean().default(false),
        })
        .strict()
        .parse(await jsonBody(req));
      check(b.size <= maxBytes(), 413, "Archivo demasiado grande.");
      check(
        mimeExtensions[b.mime]?.includes(
          b.name.split(".").pop()!.toLowerCase(),
        ),
        400,
        "Tipo de archivo no admitido.",
      );
      const identity = randomUUID();
      const key = `inputs/${identity}/source.${b.name.split(".").pop()!.toLowerCase()}`;
      const a: Asset = { ...b, id: identity, key, created_at: now() };
      await db(
        "INSERT INTO assets (id,owner_id,status,created_at,data) VALUES ($1,$2,$3,$4,$5)",
        [identity, owner, "uploading", now(), JSON.stringify(a)],
      );
      return response(
        {
          id: identity,
          key,
          mode: remote() ? "remote" : "local",
          token: remote() ? await uploadToken(key, b.mime, b.size) : undefined,
        },
        201,
      );
    }
    if (p[1]) id.parse(p[1]);
    if (method === "PUT" && p[2] === "file") {
      const row = await one(
        "SELECT * FROM assets WHERE id=$1 AND owner_id=$2 AND status=$3",
        [p[1], owner, "uploading"],
      );
      check(row, 404, "Subida no disponible.");
      const a = unpack<Asset>(row);
      const result = await saveLocal(a.key, req.body, a.size);
      check(result.size === a.size, 400, "Subida incompleta.");
      await db("UPDATE assets SET data=$1,status=$2 WHERE id=$3", [
        JSON.stringify({ ...a, ...result }),
        "ready",
        a.id,
      ]);
      return response({ id: a.id, ...result });
    }
    if (method === "POST" && p[2] === "complete") {
      const row = await one(
        "SELECT * FROM assets WHERE id=$1 AND owner_id=$2",
        [p[1], owner],
      );
      check(row, 404, "Archivo inexistente.");
      const a = unpack<Asset>(row);
      const details = await info(a.key);
      check(details.size === a.size, 400, "Tamaño de subida incorrecto.");
      await db("UPDATE assets SET status=$1 WHERE id=$2", ["ready", a.id]);
      return response({ id: a.id });
    }
    if (method === "PATCH" && p[1]) {
      const a = await asset(p[1]);
      const patch = z
        .object({
          approved: z.boolean(),
          rights: z.string().max(2000),
          tags: z.array(z.string().max(80)).max(20),
          demo: z.boolean(),
        })
        .strict()
        .parse(await jsonBody(req));
      check(
        !patch.approved || patch.rights.trim(),
        400,
        "Indicá procedencia/derechos antes de aprobar.",
      );
      await db("UPDATE assets SET data=$1 WHERE id=$2 AND owner_id=$3", [
        JSON.stringify({ ...a, ...patch }),
        a.id,
        owner,
      ]);
      return response({ ok: true });
    }
    if (["GET", "HEAD"].includes(method) && p[2] === "file") {
      const a = await asset(p[1]);
      return streamFile(req, a.key, a.mime);
    }
  }
  if (p[0] === "projects" && method === "DELETE" && p[1]) {
    id.parse(p[1]);
    await deleteProject(p[1]);
    return response({ ok: true });
  }
  if (p[0] === "maintenance" && method === "POST")
    return response({ removed: await cleanupAbandonedUploads() });
  if (p[0] === "projects" && method === "GET")
    return response(
      await db(
        "SELECT id,content_id,created_at,data FROM projects WHERE owner_id=$1 ORDER BY created_at DESC",
        [owner],
      ),
    );
  if (p[0] === "jobs") {
    if (method === "GET" && !p[1])
      return response(
        await Promise.all(
          (
            await db(
              "SELECT * FROM jobs WHERE owner_id=$1 ORDER BY created_at DESC LIMIT 100",
              [owner],
            )
          ).map(publicJob),
        ),
      );
    if (method === "POST" && !p[1]) {
      const b = z
        .object({
          content_id: z.string().max(80),
          settings: z.unknown(),
          intent_key: z.string(),
          project_id: id.optional(),
        })
        .strict()
        .parse(await jsonBody(req));
      return response(
        await publicJob(
          await createJob(b.content_id, b.settings, b.intent_key, b.project_id),
        ),
        201,
      );
    }
    if (p[1]) id.parse(p[1]);
    const row = await job(p[1]),
      data = unpack<JobData>(row);
    if (method === "GET" && !p[2]) return response(await publicJob(row));
    if (method === "POST" && p[2] === "cancel") {
      if (row.status === "queued")
        await db(
          "UPDATE jobs SET status='canceled' WHERE id=$1 AND status='queued'",
          [p[1]],
        );
      else if (row.lease_hash)
        await db(
          "UPDATE jobs SET status='cancel_requested' WHERE id=$1 AND lease_hash IS NOT NULL",
          [p[1]],
        );
      else throw new HttpError(409, "El trabajo ya terminó.");
      await event(p[1], "cancel_requested");
      return response({ ok: true });
    }
    if (method === "POST" && p[2] === "retry") {
      check(
        ["failed", "canceled"].includes(String(row.status)),
        409,
        "Solo se reintentan trabajos detenidos.",
      );
      const b = await jsonBody(req);
      return response(
        await publicJob(
          await createJob(
            data.content.id,
            { ...data.settings, parent_job_id: p[1] },
            b.intent_key,
            String(row.project_id),
          ),
        ),
        201,
      );
    }
    if (method === "PATCH" && p[2] === "plan") {
      const b = await jsonBody(req);
      return response(
        await publicJob(
          await createJob(
            data.content.id,
            { ...data.settings, ...b.settings, parent_job_id: p[1] },
            b.intent_key,
            String(row.project_id),
          ),
        ),
        201,
      );
    }
    if (method === "POST" && p[2] === "approve") {
      check(row.status === "final_ready", 409, "Primero generá el final.");
      const b = await jsonBody(req);
      check(
        b.reviewed === true,
        400,
        "Confirmá la revisión audiovisual completa.",
      );
      await db("UPDATE jobs SET data=$1 WHERE id=$2 AND owner_id=$3", [
        JSON.stringify({ ...data, reviewed: true }),
        p[1],
        owner,
      ]);
      await event(p[1], "reviewed");
      return response({ status: "ready_for_manual_post" });
    }
  }
  if (p[0] === "outputs" && ["GET", "HEAD"].includes(method)) {
    verifyMediaLink(url, p[1]);
    id.parse(p[1]);
    const row = await one(
      "SELECT outputs.* FROM outputs JOIN jobs ON jobs.id=outputs.job_id WHERE outputs.id=$1 AND outputs.owner_id=$2 AND jobs.status IN ($3,$4)",
      [p[1], owner, "preview_ready", "final_ready"],
    );
    check(row, 404, "Salida no disponible.");
    const output = unpack<Output>(row);
    return streamFile(
      req,
      output.key,
      "video/mp4",
      url.searchParams.has("download")
        ? `${output.kind === "preview" ? "VIDEO_PREVIEW" : "VIDEO_BORRADOR"}_${output.id}.mp4`
        : undefined,
    );
  }
  if (p[0] === "worker") {
    if (method === "GET" && p[1] === "status") {
      await db("SELECT 1 AS ready");
      return response({
        ready: !remote() || Boolean(process.env.BLOB_READ_WRITE_TOKEN),
        mode: remote() ? "remote" : "local",
      });
    }
    if (method === "POST" && p[1] === "lease") {
      const b = z
        .object({
          worker_id: z.string().regex(/^[a-zA-Z0-9_-]{1,80}$/),
          capabilities: z
            .record(z.string(), z.union([z.string().max(150), z.boolean()]))
            .default({}),
        })
        .strict()
        .parse(await jsonBody(req));
      return response({ job: await lease(b.worker_id, b.capabilities) });
    }
    id.parse(p[1]);
    const token = req.headers.get("x-lease-token") || "";
    // A lost HTTP response must not turn an already committed output into a failure.
    if (method === "POST" && p[2] === "finish") {
      const completed = await job(p[1]);
      if (["preview_ready", "final_ready"].includes(String(completed.status))) {
        const body = await jsonBody(req);
        const output = await one(
          "SELECT data FROM outputs WHERE job_id=$1 AND owner_id=$2",
          [p[1], owner],
        );
        check(
          output &&
            unpack<Output>(output).sha256 === body.sha256 &&
            unpack<Output>(output).size === body.size,
          409,
          "La salida ya finalizada no coincide.",
        );
        return response({ ok: true });
      }
    }
    const row = await requireLease(p[1], token),
      data = unpack<JobData>(row);
    if (method === "POST" && p[2] === "heartbeat") {
      await db(
        "UPDATE jobs SET lease_until=$1 WHERE id=$2 AND lease_hash=$3 AND lease_until>$4",
        [now() + 120000, p[1], hash(token), now()],
      );
      await db("UPDATE workers SET last_seen=$1 WHERE id=$2", [
        now(),
        row.worker_id,
      ]);
      return response({ cancel: row.status === "cancel_requested" });
    }
    if (method === "POST" && p[2] === "progress") {
      const b = z
        .object({ phase: z.enum(phases) })
        .strict()
        .parse(await jsonBody(req));
      check(
        !b.phase.endsWith("_ready"),
        400,
        "La disponibilidad se confirma al finalizar.",
      );
      await changeLease(p[1], token, b.phase);
      return response({ ok: true });
    }
    if (method === "GET" && p[2] === "assets") {
      const allowed = [
        data.settings.asset_id,
        data.settings.music_asset_id,
        ...data.settings.scenes.map((s) => s.asset_id),
      ];
      check(allowed.includes(p[3]), 403, "Recurso fuera del trabajo.");
      const a = await asset(p[3]);
      return streamFile(req, a.key, a.mime);
    }
    const outputKey = `outputs/${p[1]}/${row.attempt}_${data.settings.kind}.mp4`;
    if (method === "POST" && p[2] === "upload-token") {
      const b = z
        .object({ size: z.number().int().positive().max(maxBytes()) })
        .strict()
        .parse(await jsonBody(req));
      return response({
        key: outputKey,
        mode: remote() ? "remote" : "local",
        token: remote()
          ? await uploadToken(outputKey, "video/mp4", b.size)
          : undefined,
      });
    }
    if (method === "PUT" && p[2] === "output") {
      check(row.status !== "cancel_requested", 409, "Cancelación solicitada.");
      return response(await saveLocal(outputKey, req.body));
    }
    if (method === "POST" && p[2] === "finish") {
      check(row.status !== "cancel_requested", 409, "Cancelación solicitada.");
      const b = z
        .object({
          sha256: z.string().regex(/^[a-f0-9]{64}$/),
          size: z.number().int().positive(),
          duration: z
            .number()
            .positive()
            .max(maxDuration() + 1),
          resolution: z.tuple([z.number().int(), z.number().int()]),
          source_sha256: z.string().regex(/^[a-f0-9]{64}$/),
          validation: z.literal("probe+full_decode_passed"),
          report: z.object({
            words: z.array(word).max(15000),
            captions: z
              .array(
                z.object({
                  start: z.number(),
                  end: z.number(),
                  text: z.string().max(200),
                }),
              )
              .max(10000),
            events: z.array(z.record(z.string(), z.unknown())).max(200),
            time_map: z.array(z.record(z.string(), z.number())).max(1000),
            decisions: z.array(z.record(z.string(), z.unknown())).max(200),
            source_sha256: z.string().regex(/^[a-f0-9]{64}$/),
            source_duration: z
              .number()
              .positive()
              .max(maxDuration() + 1),
            warnings: z.array(z.string().max(800)).max(500),
          }),
        })
        .strict()
        .parse(await jsonBody(req));
      const expected =
        data.settings.kind === "final" ? [1080, 1920] : [360, 640];
      check(
        b.resolution.every((n, i) => n === expected[i]),
        400,
        "Resolución incorrecta.",
      );
      const details = await info(outputKey);
      check(details.size === b.size, 400, "Salida incompleta.");
      check(
        b.report.source_sha256 === b.source_sha256,
        400,
        "Identidad de fuente inconsistente.",
      );
      const output: Output = {
        id: randomUUID(),
        kind: data.settings.kind,
        key: outputKey,
        ...b,
      };
      // Keep report separate from downloadable metadata, and never expose storage paths.
      delete (output as Output & { report?: unknown }).report;
      await transaction(async () => {
        await changeLease(p[1], token, "uploading", {
          ...data,
          report: b.report,
          warnings: b.report.warnings,
        });
        await db(
          "INSERT INTO outputs (id,job_id,owner_id,kind,created_at,data) VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT(job_id,kind) DO UPDATE SET id=excluded.id,created_at=excluded.created_at,data=excluded.data",
          [output.id, p[1], owner, output.kind, now(), JSON.stringify(output)],
        );
        await db(
          "INSERT INTO editorial_plans (id,project_id,job_id,owner_id,created_at,data) VALUES ($1,$2,$3,$4,$5,$6)",
          [
            randomUUID(),
            row.project_id,
            p[1],
            owner,
            now(),
            JSON.stringify(b.report),
          ],
        );
        const finished = await db(
          "UPDATE jobs SET status=$1,lease_hash=NULL,lease_until=NULL,updated_at=$2 WHERE id=$3 AND lease_hash=$4 AND status<>$5 RETURNING id",
          [
            data.settings.kind + "_ready",
            now(),
            p[1],
            hash(token),
            "cancel_requested",
          ],
        );
        check(
          finished.length,
          409,
          "El trabajo fue cancelado antes de finalizar.",
        );
        await event(p[1], data.settings.kind + "_ready");
      });
      return response({ ok: true });
    }
    if (method === "POST" && p[2] === "fail") {
      const b = z
        .object({
          code: z.enum([
            "render_failed",
            "canceled",
            "invalid_media",
            "timeout",
            "disk_full",
            "engine_unavailable",
          ]),
        })
        .strict()
        .parse(await jsonBody(req));
      const messages = {
        render_failed:
          "Falló el render. Revisá el diagnóstico local y reintentá.",
        canceled: "Cancelado por el propietario.",
        invalid_media: "La fuente no cumple formato, duración o SHA.",
        timeout: "El proceso superó el tiempo permitido.",
        disk_full: "El equipo necesita más espacio libre.",
        engine_unavailable:
          "Motor no disponible. Instalá Remotion o elegí Básico FFmpeg.",
      };
      await db(
        "UPDATE jobs SET status=$1,data=$2,lease_hash=NULL,lease_until=NULL,updated_at=$3 WHERE id=$4 AND lease_hash=$5",
        [
          b.code === "canceled" ? "canceled" : "failed",
          JSON.stringify({ ...data, error: messages[b.code] }),
          now(),
          p[1],
          hash(token),
        ],
      );
      await event(p[1], b.code);
      return response({ ok: true });
    }
  }
  throw new HttpError(404, "Ruta no encontrada.");
}
async function handler(req: Request) {
  try {
    return await dispatch(req);
  } catch (e) {
    if (e instanceof ZodError)
      return response(
        {
          error: "Revisá los datos.",
          details: e.issues
            .map((i) => `${i.path.join(".")}: ${i.message}`)
            .slice(0, 8),
        },
        400,
      );
    if (e instanceof HttpError) return response({ error: e.message }, e.status);
    console.error(
      "studio_request_failed",
      e instanceof Error ? e.name : "unknown",
    );
    return response(
      { error: "No se pudo completar. Revisá la configuración del servidor." },
      500,
    );
  }
}
export {
  handler as GET,
  handler as HEAD,
  handler as POST,
  handler as PUT,
  handler as PATCH,
  handler as DELETE,
};
