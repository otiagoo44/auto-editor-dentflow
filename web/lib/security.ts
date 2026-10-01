import {
  timingSafeEqual,
  createHash,
  createHmac,
  randomBytes,
} from "node:crypto";
import { remote } from "./config";
export class HttpError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export function check(
  value: unknown,
  status: number,
  message: string,
): asserts value {
  if (!value) throw new HttpError(status, message);
}
export const hash = (value: string | Buffer) =>
  createHash("sha256").update(value).digest("hex");
const equal = (a: string, b: string) =>
  timingSafeEqual(Buffer.from(hash(a)), Buffer.from(hash(b)));
const localMediaSecret = randomBytes(32).toString("hex");
function mediaSecret() {
  const secret = process.env.MEDIA_SIGNING_SECRET || process.env.WORKER_TOKEN;
  check(
    !remote() || Boolean(secret && secret.length >= 32),
    503,
    "Falta firma privada de medios.",
  );
  return secret || localMediaSecret;
}
export function mediaLink(id: string, expires = Date.now() + 15 * 60000) {
  const signature = createHmac("sha256", mediaSecret())
    .update(`${id}:${expires}`)
    .digest("hex");
  return `/api/outputs/${id}?expires=${expires}&signature=${signature}`;
}
export function verifyMediaLink(url: URL, id: string) {
  const expires = Number(url.searchParams.get("expires"));
  check(
    Number.isFinite(expires) &&
      expires > Date.now() &&
      expires <= Date.now() + 15 * 60000,
    403,
    "Enlace vencido. Actualizá el proyecto.",
  );
  const expected = new URL(
    mediaLink(id, expires),
    "http://localhost",
  ).searchParams.get("signature")!;
  check(
    equal(url.searchParams.get("signature") || "", expected),
    403,
    "Firma inválida.",
  );
}
export function isWorker(req: Request) {
  const token = process.env.WORKER_TOKEN;
  return Boolean(
    token &&
    token.length >= 32 &&
    equal(req.headers.get("authorization") || "", `Bearer ${token}`),
  );
}
export function authorize(req: Request, worker = false) {
  const url = new URL(req.url);
  if (worker) {
    check(isWorker(req), 401, "Agente no autorizado.");
    return;
  }
  const host = req.headers.get("host") || url.host;
  if (!remote()) {
    check(!process.env.VERCEL, 503, "Configura REMOTE_STUDIO para desplegar.");
    check(
      /^(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$/.test(host),
      403,
      "Studio local solo admite loopback.",
    );
  } else {
    const password = process.env.OWNER_PASSWORD;
    check(
      password && password.length >= 32,
      503,
      "Configura la protección de propietario.",
    );
    const expected =
      "Basic " +
      Buffer.from(`${process.env.OWNER_USER || "owner"}:${password}`).toString(
        "base64",
      );
    check(
      equal(req.headers.get("authorization") || "", expected),
      401,
      "Acceso exclusivo del propietario.",
    );
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(req.method)) {
    const origin = req.headers.get("origin");
    // Browser mutations require same origin; CLI requests without browser metadata are allowed locally.
    check(
      !origin || new URL(origin).host === host,
      403,
      "Origen no autorizado.",
    );
    check(
      !["cross-site", "same-site"].includes(
        req.headers.get("sec-fetch-site") || "",
      ),
      403,
      "Solicitud cruzada no permitida.",
    );
  }
}
export async function jsonBody(req: Request) {
  check(
    Number(req.headers.get("content-length") || 0) <= 2_000_000,
    413,
    "Solicitud demasiado grande.",
  );
  const reader = req.body?.getReader();
  let size = 0;
  const chunks: Uint8Array[] = [];
  if (reader)
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > 2_000_000) {
        await reader.cancel();
        throw new HttpError(413, "Solicitud demasiado grande.");
      }
      chunks.push(value);
    }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new HttpError(400, "JSON inválido.");
  }
}
