import { db, one, transaction, unpack } from "./db";
import { Asset, JobData, Output } from "./contracts";
import { owner } from "./config";
import { check } from "./security";
import { remove } from "./storage";

/** Idempotent deletion; block rendering before deleting any project media. */
export async function deleteProject(projectId: string) {
  await transaction(async () => {
    const project = await one(
      "UPDATE projects SET data=data WHERE id=$1 AND owner_id=$2 RETURNING *",
      [projectId, owner],
    );
    check(project, 404, "Proyecto no encontrado.");
    const active = await one(
      "SELECT id FROM jobs WHERE project_id=$1 AND status NOT IN ('preview_ready','final_ready','failed','canceled')",
      [projectId],
    );
    check(
      !active,
      409,
      "Cancelá el trabajo activo y esperá su confirmación antes de borrar.",
    );
    await db("UPDATE projects SET data=$1 WHERE id=$2 AND owner_id=$3", [
      JSON.stringify({
        ...unpack<Record<string, unknown>>(project),
        deleting: true,
      }),
      projectId,
      owner,
    ]);
  });
  // Retain metadata until every file has been removed, so a network error is retryable.
  const outputs = await db(
    "SELECT outputs.* FROM outputs JOIN jobs ON jobs.id=outputs.job_id WHERE jobs.project_id=$1 AND outputs.owner_id=$2",
    [projectId, owner],
  );
  for (const output of outputs) await remove(unpack<Output>(output).key);
  await transaction(async () => {
    await db(
      "DELETE FROM outputs WHERE job_id IN (SELECT id FROM jobs WHERE project_id=$1) AND owner_id=$2",
      [projectId, owner],
    );
    await db(
      "DELETE FROM editorial_plans WHERE project_id=$1 AND owner_id=$2",
      [projectId, owner],
    );
    await db(
      "DELETE FROM job_events WHERE job_id IN (SELECT id FROM jobs WHERE project_id=$1)",
      [projectId],
    );
    await db("DELETE FROM jobs WHERE project_id=$1 AND owner_id=$2", [
      projectId,
      owner,
    ]);
    await db("DELETE FROM projects WHERE id=$1 AND owner_id=$2", [
      projectId,
      owner,
    ]);
  });
}

/** Only abandoned uploads expire automatically; completed sources remain explicit. */
export async function cleanupAbandonedUploads() {
  const rows = await db(
    "SELECT * FROM assets WHERE owner_id=$1 AND status='uploading' AND created_at<$2",
    [owner, Date.now() - 86400000],
  );
  for (const row of rows) {
    const asset = unpack<Asset>(row);
    await remove(asset.key);
    await db(
      "DELETE FROM assets WHERE id=$1 AND owner_id=$2 AND status='uploading'",
      [row.id, owner],
    );
  }
  return rows.length;
}

export async function deleteAsset(assetId: string) {
  const row = await transaction(async () => {
    const row = await one(
      "UPDATE assets SET status=status WHERE id=$1 AND owner_id=$2 RETURNING *",
      [assetId, owner],
    );
    check(row, 404, "Recurso no encontrado.");
    const jobs = await db("SELECT data FROM jobs WHERE owner_id=$1", [owner]);
    check(
      !jobs.some((r) => {
        const s = unpack<JobData>(r).settings;
        return [
          s.asset_id,
          s.music_asset_id,
          ...s.scenes.map((scene) => scene.asset_id),
        ].includes(assetId);
      }),
      409,
      "Este recurso todavía pertenece a un montaje. Borrá sus proyectos primero.",
    );
    await db(
      "UPDATE assets SET status='deleting' WHERE id=$1 AND owner_id=$2",
      [assetId, owner],
    );
    return row;
  });
  await remove(unpack<Asset>(row).key);
  await db("DELETE FROM assets WHERE id=$1 AND owner_id=$2", [assetId, owner]);
}
