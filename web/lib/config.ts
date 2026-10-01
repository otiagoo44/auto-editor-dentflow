import path from "node:path";
import os from "node:os";
export const remote = () => process.env.STUDIO_MODE === "REMOTE_STUDIO";
export const dataDir = () =>
  path.resolve(
    process.env.STUDIO_DATA_DIR ||
      path.join(process.env.LOCALAPPDATA || os.homedir(), "DentFlow", "studio"),
  );
export const owner = "owner";
export const maxBytes = () =>
  Number(process.env.MAX_UPLOAD_MB || 1024) * 1024 * 1024;
export const maxDuration = () =>
  Number(process.env.MAX_DURATION_SECONDS || 600);
export const now = () => Date.now();
