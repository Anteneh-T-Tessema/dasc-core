#!/usr/bin/env node
import { Command } from "commander";
import { BitemporalLedger } from "./ledger.js";
import * as crypto from "crypto";
import * as fs from "fs";

const program = new Command();
const ledger = new BitemporalLedger();

program
  .name("@antenehtessema/dasc-core")
  .description("DASC-Core Node.js CLI - Deterministic Agentic Safety Controller")
  .version("1.0.0");

program
  .command("inspect")
  .description("Inspect the last decisions in the ledger")
  .option("-l, --limit <number>", "Number of records to show", "10")
  .action((options) => {
    const history = ledger.getHistory(parseInt(options.limit));
    console.log("\n=== DASC Ledger Inspection ===");
    history.forEach((row: any) => {
      console.log(`[${row.timestamp}] ${row.intent_id} | ${row.actor_agent} | ${row.status}`);
      if (row.reason_codes && row.status !== 'COMMIT') {
          console.log(`  Reason: ${row.reason_codes}`);
      }
    });
    console.log("==============================\n");
  });

program
  .command("hash <file>")
  .description("Generate a DASC-compatible hash for a file for Semantic OCC")
  .action((file) => {
    try {
      const fileBuffer = fs.readFileSync(file);
      const hash = crypto.createHash("sha256").update(fileBuffer).digest("hex");
      console.log(`hash:${hash}`);
    } catch (err: any) {
      console.error(`Error reading file: ${err.message}`);
    }
  });

program.parse();
