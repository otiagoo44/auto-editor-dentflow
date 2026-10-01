import { createReadStream, createWriteStream } from "node:fs";
import { mkdir, stat, unlink, rename } from "node:fs/promises";
import path from "node:path";
import { Readable, Transform } from "node:stream";
import { pipeline } from "node:stream/promises";
import { createHash, randomUUID } from "node:crypto";
import { get, head, del } from "@vercel/blob";
import { generateClientTokenFromReadWriteToken } from "@vercel/blob/client";
import { dataDir, remote, maxBytes } from "./config";
import { check } from "./security";

export function localPath(key: string) {
  check(
    /^(inputs|outputs)\/[a-f0-9-]{36}\/[a-z0-9_.-]+$/.test(key),
    400,
    "Identificador de archivo inválido.",
  );
  return path.join(dataDir(), ...key.split("/"));
}
export async function saveLocal(
  key: string,
  body: ReadableStream<Uint8Array> | null,
  limit = maxBytes(),
) {
  check(!remote(), 400, "Usá subida directa al almacenamiento privado.");
  check(body, 400, "Archivo vacío.");
  const dest = localPath(key);
  await mkdir(path.dirname(dest), { recursive: true });
  const partial = dest + "." + randomUUID() + ".partial";
  const digest = createHash("sha256");
  let size = 0;
  try {
    await pipeline(
      Readable.fromWeb(body as never),
      new Transform({
        transform(chunk, _, cb) {
          size += chunk.length;
          if (size > limit) {
            cb(new Error("Archivo supera el límite."));
            return;
          }
          digest.update(chunk);
          cb(null, chunk);
        },
      }),
      createWriteStream(partial, { flags: "wx" }),
    );
    check(size > 0, 400, "Archivo vacío.");
    await rename(partial, dest);
    return { size, sha256: digest.digest("hex") };
  } catch (e) {
    await unlink(partial).catch(() => {});
    throw e;
  }
}
export async function uploadToken(key: string, mime: string, size: number) {
  check(remote(), 400, "Token exclusivo del modo remoto.");
  return generateClientTokenFromReadWriteToken({
    token: process.env.BLOB_READ_WRITE_TOKEN!,
    pathname: key,
    allowedContentTypes: [mime],
    maximumSizeInBytes: size,
    validUntil: Date.now() + 15 * 60 * 1000,
    addRandomSuffix: false,
    allowOverwrite: false,
  });
}
export async function info(key: string) {
  if (remote()) {
    const h = await head(key);
    check(
      new URL(h.url).hostname.endsWith(".private.blob.vercel-storage.com"),
      400,
      "El almacén debe ser privado.",
    );
    return { size: h.size, mime: h.contentType };
  }
  return {
    size: (await stat(localPath(key))).size,
    mime: "application/octet-stream",
  };
}
export async function remove(key: string) {
  if (remote()) await del(key);
  else await unlink(localPath(key)).catch(() => {});
}
export async function streamFile(
  req: Request,
  key: string,
  mime: string,
  filename?: string,
) {
  const headers = new Headers({
    "Content-Type": mime,
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
    "Accept-Ranges": "bytes",
  });
  if (filename)
    headers.set("Content-Disposition", `attachment; filename="${filename}"`);
  if (remote()) {
    const result = await get(key, {
      access: "private",
      headers: req.headers.has("range")
        ? { Range: req.headers.get("range")! }
        : undefined,
    });
    check(result?.statusCode === 200, 404, "Archivo no disponible.");
    for (const h of ["content-length", "content-range"])
      if (result.headers.has(h)) headers.set(h, result.headers.get(h)!);
    return new Response(req.method === "HEAD" ? null : result.stream, {
      status: headers.has("content-range") ? 206 : 200,
      headers,
    });
  }
  const file = localPath(key);
  const { size } = await stat(file);
  let start = 0,
    end = size - 1,
    status = 200;
  const range = req.headers.get("range");
  if (range) {
    const m = /^bytes=(\d*)-(\d*)$/.exec(range);
    check(m && (m[1] || m[2]), 416, "Rango inválido.");
    if (!m[1]) start = Math.max(0, size - Number(m[2]));
    else {
      start = Number(m[1]);
      if (m[2]) end = Math.min(end, Number(m[2]));
    }
    check(start <= end && start < size, 416, "Rango fuera del archivo.");
    status = 206;
    headers.set("Content-Range", `bytes ${start}-${end}/${size}`);
  }
  headers.set("Content-Length", String(end - start + 1));
  return new Response(
    req.method === "HEAD"
      ? null
      : (Readable.toWeb(
          createReadStream(file, { start, end }),
        ) as ReadableStream),
    { status, headers },
  );
}
