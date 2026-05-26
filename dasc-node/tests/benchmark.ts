import { Kernel } from "../src/kernel.js";
import { Intent } from "../src/types.js";
import { performance } from "perf_hooks";

const kernel = new Kernel();
const iterations = 1000;

const intent: Intent = {
  intent_id: "bench-",
  actor_agent: "benchmark-bot",
  action_type: "NOP",
  risk_tier: 1,
  evidence: [{ source_type: "trusted" }],
  payload: { data: "test" }
};

console.log(`🚀 Starting DASC Benchmark (${iterations} iterations)...`);

const start = performance.now();

for (let i = 0; i < iterations; i++) {
  intent.intent_id = `bench-${i}`;
  kernel.evaluate(intent);
}

const end = performance.now();
const totalTime = end - start;
const avgTime = totalTime / iterations;

console.log("------------------------------------------");
console.log(`✅ Benchmark Complete!`);
console.log(`Total Time: ${totalTime.toFixed(2)}ms`);
console.log(`Avg Latency: ${avgTime.toFixed(4)}ms per evaluation`);
console.log(`Throughput: ${(1000 / avgTime).toFixed(0)} evaluations/sec`);
console.log("------------------------------------------");
