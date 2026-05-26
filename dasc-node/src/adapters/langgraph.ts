import { Kernel } from "../kernel.js";
import { Intent, Decision } from "../types.js";
import { v4 as uuidv4 } from "uuid";
import { BaseCheckpointSaver, Checkpoint, CheckpointTuple } from "@langchain/langgraph";
import Database from "better-sqlite3";

/**
 * LangGraph.js Adapter
 * 
 * Provides a 'Safety Guard' node that can be injected into any StateGraph.
 */

export interface DASCState {
  proposed_intent?: Intent;
  last_decision?: Decision;
  error?: string;
}

export class DASCLangGraphAdapter {
  private kernel: Kernel;

  constructor(kernel: Kernel) {
    this.kernel = kernel;
  }

  /**
   * The Safety Guard Node
   * Injects into the graph to evaluate the proposed intent in the state.
   */
  public safetyNode = async (state: DASCState): Promise<Partial<DASCState>> => {
    if (!state.proposed_intent) {
      return { error: "No intent proposed for evaluation." };
    }

    // Ensure intent has an ID
    if (!state.proposed_intent.intent_id) {
      state.proposed_intent.intent_id = uuidv4();
    }

    const decision = this.kernel.evaluate(state.proposed_intent);

    return {
      last_decision: decision
    };
  };

  /**
   * Conditional Edge logic
   * Routes the graph based on the DASC decision.
   */
  public routeDecision = (state: DASCState): string => {
    const status = state.last_decision?.status;
    if (status === "COMMIT") return "authorized";
    if (status === "ESCALATE") return "human_gate";
    return "rejected";
  };
}

export class DASCLangGraphCheckpointer extends BaseCheckpointSaver {
  private db: Database.Database;

  constructor(dbPath: string = "dasc_ledger_node.db") {
    super();
    this.db = new Database(dbPath);
    this.init();
  }

  private init() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS langgraph_checkpoints (
        thread_id TEXT,
        checkpoint_id TEXT,
        parent_id TEXT,
        checkpoint_blob TEXT,
        metadata_blob TEXT,
        timestamp TEXT,
        PRIMARY KEY (thread_id, checkpoint_id)
      )
    `);
  }

  async getTuple(config: any): Promise<CheckpointTuple | undefined> {
    const thread_id = config.configurable?.thread_id;
    const checkpoint_id = config.configurable?.checkpoint_id;

    if (!thread_id) return undefined;

    let row: any;
    if (checkpoint_id) {
      row = this.db.prepare(
        "SELECT parent_id, checkpoint_blob, metadata_blob FROM langgraph_checkpoints WHERE thread_id = ? AND checkpoint_id = ?"
      ).get(thread_id, checkpoint_id);
    } else {
      row = this.db.prepare(
        "SELECT parent_id, checkpoint_blob, metadata_blob, checkpoint_id FROM langgraph_checkpoints WHERE thread_id = ? ORDER BY timestamp DESC LIMIT 1"
      ).get(thread_id);
    }

    if (!row) return undefined;

    const actual_checkpoint_id = checkpoint_id || row.checkpoint_id;
    
    return {
      config: {
        configurable: {
          thread_id,
          checkpoint_id: actual_checkpoint_id
        }
      },
      checkpoint: JSON.parse(row.checkpoint_blob) as Checkpoint,
      metadata: row.metadata_blob ? JSON.parse(row.metadata_blob) : {},
      parentConfig: row.parent_id ? {
        configurable: {
          thread_id,
          checkpoint_id: row.parent_id
        }
      } : undefined
    };
  }

  async put(config: any, checkpoint: Checkpoint, metadata: any): Promise<any> {
    const thread_id = config.configurable?.thread_id;
    const checkpoint_id = checkpoint.id;
    const parent_id = config.configurable?.checkpoint_id;

    if (!thread_id || !checkpoint_id) {
      throw new Error("Missing thread_id or checkpoint_id");
    }

    const checkpoint_blob = JSON.stringify(checkpoint);
    const metadata_blob = JSON.stringify(metadata || {});
    const timestamp = checkpoint.ts || new Date().toISOString();

    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO langgraph_checkpoints (thread_id, checkpoint_id, parent_id, checkpoint_blob, metadata_blob, timestamp)
      VALUES (?, ?, ?, ?, ?, ?)
    `);

    stmt.run(thread_id, checkpoint_id, parent_id, checkpoint_blob, metadata_blob, timestamp);

    return {
      configurable: {
        thread_id,
        checkpoint_id
      }
    };
  }

  async *list(config: any, options?: any): AsyncGenerator<CheckpointTuple, void, unknown> {
    const thread_id = config.configurable?.thread_id;
    if (!thread_id) return;

    let query = "SELECT parent_id, checkpoint_blob, metadata_blob, checkpoint_id FROM langgraph_checkpoints WHERE thread_id = ?";
    const params: any[] = [thread_id];

    if (options?.before) {
      query += " AND timestamp < ?";
      params.push(options.before.configurable?.checkpoint_id);
    }

    query += " ORDER BY timestamp DESC";
    if (options?.limit) {
      query += ` LIMIT ${options.limit}`;
    }

    const rows = this.db.prepare(query).all(...params) as any[];

    for (const row of rows) {
      yield {
        config: {
          configurable: {
            thread_id,
            checkpoint_id: row.checkpoint_id
          }
        },
        checkpoint: JSON.parse(row.checkpoint_blob) as Checkpoint,
        metadata: row.metadata_blob ? JSON.parse(row.metadata_blob) : {},
        parentConfig: row.parent_id ? {
          configurable: {
            thread_id,
            checkpoint_id: row.parent_id
          }
        } : undefined
      };
    }
  }
}
