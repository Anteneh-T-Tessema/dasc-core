import { Intent, Decision } from "./types.js";

/**
 * DASC Remote Client
 * Allows Node.js agents to submit intents to a centralized Safety Server.
 */
export class DASCClient {
  private baseUrl: string;
  private apiKey?: string;

  constructor(baseUrl: string = "http://localhost:3000", apiKey?: string) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  async evaluate(intent: Intent): Promise<Decision> {
    const response = await fetch(`${this.baseUrl}/evaluate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(this.apiKey ? { "X-API-KEY": this.apiKey } : {}),
      },
      body: JSON.stringify(intent),
    });

    if (!response.ok) {
      throw new Error(`DASC_CLIENT_ERROR: ${response.statusText}`);
    }

    return await response.json() as Decision;
  }
}
