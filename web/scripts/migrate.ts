import { db } from "../lib/db";
await db("SELECT 1");
console.log("Migraciones Studio aplicadas.");
process.exit(0);
