export type DASCStatus = "COMMIT" | "REJECT" | "ESCALATE";

export interface Evidence {
  source_type: "trusted" | "untrusted";
  content_hash?: string;
  metadata?: Record<string, any>;
}

export interface Intent {
  intent_id: string;
  actor_agent: string;
  action_type: string;
  risk_tier: number;
  state_version_vector?: Record<string, string>;
  evidence: Evidence[];
  compensation_plan?: Record<string, string>;
  payload: any;
}

export interface Decision {
  intent_id: string;
  status: DASCStatus;
  reason_codes: string[];
  suggestions: string[];
  timestamp: string;
}
