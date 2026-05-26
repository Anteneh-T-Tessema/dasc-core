import { Intent } from "../types.js";
import * as fs from "fs";
import * as path from "path";

function getFieldValue(obj: any, fieldPath: string): any {
  const parts = fieldPath.trim().split(".");
  let current = obj;
  for (const part of parts) {
    if (current === undefined || current === null) return undefined;
    current = current[part];
  }
  return current;
}

function parseVal(valStr: string): any {
  valStr = valStr.trim();
  if (valStr.toLowerCase() === "true") return true;
  if (valStr.toLowerCase() === "false") return false;
  if (
    (valStr.startsWith("'") && valStr.endsWith("'")) ||
    (valStr.startsWith('"') && valStr.endsWith('"'))
  ) {
    return valStr.slice(1, -1);
  }

  const num = Number(valStr);
  if (!isNaN(num)) return num;
  return valStr;
}

function evaluateComparison(left: any, op: string, rightStr: string): boolean {
  if (left === undefined || left === null) {
    if (op === "!=") return true;
    return false;
  }

  const right = parseVal(rightStr);

  // Cast both to numbers if comparable
  let leftVal = left;
  let rightVal = right;
  if (typeof leftVal === "number" && typeof rightVal === "number") {
    leftVal = Number(leftVal);
    rightVal = Number(rightVal);
  }

  switch (op) {
    case "==":
      return leftVal === rightVal;
    case "!=":
      return leftVal !== rightVal;
    case ">=":
      return leftVal >= rightVal;
    case "<=":
      return leftVal <= rightVal;
    case ">":
      return leftVal > rightVal;
    case "<":
      return leftVal < rightVal;
    case "contains":
      return String(leftVal).includes(String(rightVal));
    case "in":
      if (typeof rightVal === "string") {
        const items = rightVal
          .replace("[", "")
          .replace("]", "")
          .split(",")
          .map((item) => item.trim().replace(/^['"]|['"]$/g, ""));
        return items.includes(String(leftVal));
      }
      if (Array.isArray(rightVal)) {
        return rightVal.includes(leftVal);
      }
      return false;
    default:
      return false;
  }
}

function evaluateCondition(intent: Intent, conditionStr: string): boolean {
  const comparisons = conditionStr.split(" and ");
  const operators = ["==", "!=", ">=", "<=", ">", "<", "contains", "in"];

  for (const comp of comparisons) {
    const trimmedComp = comp.trim();
    let matched = false;

    for (const op of operators) {
      if (trimmedComp.includes(` ${op} `) || trimmedComp.includes(`${op}`)) {
        // Handle whitespace around operators
        const parts = trimmedComp.split(op);
        const leftPath = parts[0].trim();
        const rightStr = parts.slice(1).join(op).trim();

        const leftVal = getFieldValue(intent, leftPath);
        if (!evaluateComparison(leftVal, op, rightStr)) {
          return false;
        }
        matched = true;
        break;
      }
    }

    if (!matched) {
      const leftVal = getFieldValue(intent, trimmedComp);
      if (!leftVal) return false;
    }
  }

  return true;
}

export interface Rule {
  name: string;
  condition: string;
  action: "COMMIT" | "REJECT" | "ESCALATE";
  reason: string;
}

export class DeclarativePolicyEngine {
  public rules: Rule[] = [];

  constructor(rulesJson?: { rules: Rule[] }) {
    if (rulesJson) {
      this.rules = rulesJson.rules;
    }
  }

  public loadRulesFromFile(filePath: string) {
    const raw = fs.readFileSync(filePath, "utf-8");
    const parsed = JSON.parse(raw);
    this.rules = parsed.rules || [];
  }

  public loadRulesFromDirectory(dirPath: string) {
    if (fs.existsSync(dirPath) && fs.statSync(dirPath).isDirectory()) {
      const files = fs.readdirSync(dirPath);
      for (const file of files) {
        if (file.endsWith(".json")) {
          try {
            const raw = fs.readFileSync(path.join(dirPath, file), "utf-8");
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed.rules)) {
              this.rules.push(...parsed.rules);
            }
          } catch (err: any) {
            console.error(`[DASC] Error loading declarative rule file ${file}: ${err.message}`);
          }
        }
      }
    }
  }

  public evaluatePolicies = (intent: Intent): { pass: boolean; reason?: string } => {
    for (const rule of this.rules) {
      if (rule.condition) {
        try {
          if (evaluateCondition(intent, rule.condition)) {
            const action = rule.action || "REJECT";
            let reason = rule.reason || "DECLARATIVE_POLICY_VIOLATION";
            if (action === "ESCALATE") {
              reason = `TIER_4_MANDATORY_ESCALATION: ${reason}`;
            }
            return { pass: false, reason };
          }
        } catch (err: any) {
          return { pass: false, reason: `RULE_EVALUATION_ERROR: ${rule.name} (${err.message})` };
        }
      }
    }
    return { pass: true };
  };
}
