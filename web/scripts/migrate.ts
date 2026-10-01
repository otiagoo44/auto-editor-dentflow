import { closeDb, db } from "../lib/db";
async function main() {
  try {
    await db("SELECT 1");
    console.log("Migraciones Studio aplicadas.");
  } finally {
    await closeDb();
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
