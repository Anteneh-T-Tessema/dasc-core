import argparse
import json
import sys
import os
from .ledger import BitemporalLedger
from .utils import calculate_file_hash
from .kernel import Kernel

def main():
    parser = argparse.ArgumentParser(description="DASC CLI - Deterministic Agentic Swarm Control")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Inspect Ledger
    inspect_parser = subparsers.add_parser("inspect", help="Inspect the bitemporal ledger")
    inspect_parser.add_argument("--db", default="dasc_ledger.db", help="Path to SQLite ledger file")
    inspect_parser.add_argument("--limit", type=int, default=10, help="Number of records to show")
    inspect_parser.add_argument("--as-of", help="Inspect ledger entries as of a specific ISO timestamp")

    # Verify Ledger Integrity
    integrity_parser = subparsers.add_parser("integrity", help="Verify the cryptographic hash-chain integrity of the ledger")
    integrity_parser.add_argument("--db", default="dasc_ledger.db", help="Path to SQLite ledger file")

    # Calculate Hash
    hash_parser = subparsers.add_parser("hash", help="Calculate SHA-256 hash for OCC")
    hash_parser.add_argument("file", help="File to hash")

    # Verify Intent
    verify_parser = subparsers.add_parser("verify", help="Manually verify an intent JSON file")
    verify_parser.add_argument("intent_file", help="Path to intent.json")
    verify_parser.add_argument("--state", help="JSON string of current state versions (optional)")

    # Serve Control Plane
    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI DASC Control Plane server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host address to bind the server to")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to listen on")

    # List Policies
    subparsers.add_parser("policies", help="List all registered/prebuilt DASC safety policies")

    # Export Ledger
    export_parser = subparsers.add_parser("export", help="Export the ledger compliance report")
    export_parser.add_argument("--db", default="dasc_ledger.db", help="Path to SQLite ledger file")
    export_parser.add_argument("--format", choices=["json", "csv", "markdown"], default="markdown", help="Format of the report (json/csv/markdown)")
    export_parser.add_argument("--out", help="Output file path (prints to stdout if omitted)")
    export_parser.add_argument("--as-of", help="Filter ledger entries as of a specific ISO timestamp")

    args = parser.parse_args()

    if args.command == "inspect":
        if not os.path.exists(args.db):
            print(f"Error: Ledger file {args.db} not found.")
            return
        
        ledger = BitemporalLedger(db_path=args.db)
        if args.as_of:
            history = ledger.get_history_as_of(args.as_of)
            print(f"\n⌛ BITEMPORAL HISTORY AS OF: {args.as_of}")
        else:
            history = ledger.get_history()
        
        print(f"\n{'TIMESTAMP':<25} | {'INTENT_ID':<15} | {'STATUS':<10} | {'AGENT':<15}")
        print("-" * 75)
        for entry in history[:args.limit]:
            print(f"{entry['timestamp']:<25} | {entry['intent_id']:<15} | {entry['status']:<10} | {entry['actor_agent']:<15}")

    elif args.command == "integrity":
        if not os.path.exists(args.db):
            print(f"Error: Ledger file {args.db} not found.")
            sys.exit(1)
        
        ledger = BitemporalLedger(db_path=args.db)
        is_valid = ledger.verify_integrity()
        if is_valid:
            print("\n✅ LEDGER INTEGRITY VALID: All cryptographic signatures and previous hash pointers match successfully.")
        else:
            print("\n❌ LEDGER CORRUPTED: Cryptographic mismatch detected! One or more records have been modified/tampered.")
            sys.exit(1)

    elif args.command == "hash":
        file_hash = calculate_file_hash(args.file)
        if file_hash:
            print(f"hash:{file_hash}")
        else:
            print(f"Error: Could not calculate hash for {args.file}")
            sys.exit(1)

    elif args.command == "verify":
        try:
            with open(args.intent_file, "r") as f:
                intent_data = json.load(f)
            
            state = {}
            if args.state:
                state = json.loads(args.state)
            
            from .schemas import Intent
            intent = Intent(**intent_data)
            kernel = Kernel(current_state_versions=state)
            decision = kernel.evaluate(intent)
            
            print(json.dumps(decision.model_dump(), indent=2))
        except Exception as e:
            print(f"Error: {str(e)}")
            sys.exit(1)

    elif args.command == "serve":
        try:
            import uvicorn
            from .server import app
            print(f"Starting DASC FastAPI server on {args.host}:{args.port}...")
            uvicorn.run(app, host=args.host, port=args.port)
        except Exception as e:
            print(f"Error starting server: {str(e)}")
            sys.exit(1)

    elif args.command == "policies":
        from .policies import cybersecurity_policy, finance_policy, healthcare_policy, privacy_policy
        print("\nPrebuilt DASC Safety Policies:")
        print("=" * 80)
        for policy in [cybersecurity_policy, finance_policy, healthcare_policy, privacy_policy]:
            print(f"Policy Name: {policy.__name__}")
            doc = policy.__doc__.strip() if policy.__doc__ else "No documentation provided."
            print(f"Description:\n{doc}")
            print("=" * 80)

        # Dynamic imperative policies from DASC_POLICIES_DIR
        POLICIES_DIR = os.getenv("DASC_POLICIES_DIR", "dasc_policies.d")
        if os.path.exists(POLICIES_DIR) and os.path.isdir(POLICIES_DIR):
            import importlib.util
            import sys
            dynamic_policies = []
            for root_dir, _, files in os.walk(POLICIES_DIR):
                for file in files:
                    if file.endswith(".py") and not file.startswith("__"):
                        file_path = os.path.join(root_dir, file)
                        module_name = f"dasc_dynamic_policy_{os.path.splitext(file)[0]}"
                        try:
                            spec = importlib.util.spec_from_file_location(module_name, file_path)
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                sys.modules[module_name] = module
                                spec.loader.exec_module(module)
                                for attr_name in dir(module):
                                    attr = getattr(module, attr_name)
                                    if callable(attr) and attr_name.endswith("_policy") and attr.__module__ == module_name:
                                        dynamic_policies.append((attr_name, attr.__doc__, file))
                        except Exception:
                            pass
            if dynamic_policies:
                print(f"\nDynamically Loaded Imperative Policies from '{POLICIES_DIR}':")
                print("=" * 80)
                for name, doc, file_src in dynamic_policies:
                    print(f"Policy Name: {name} (Source: {file_src})")
                    doc = doc.strip() if doc else "No documentation provided."
                    print(f"Description:\n{doc}")
                    print("=" * 80)
            
        # Load and print declarative policies if file/directory exists
        RULES_FILE = os.getenv("DASC_RULES_FILE", "dasc_rules.json")
        RULES_DIR = os.getenv("DASC_RULES_DIR", "dasc_rules.d")
        
        all_rules = []
        if os.path.exists(RULES_FILE):
            try:
                with open(RULES_FILE, "r") as f:
                    rules_data = json.load(f)
                all_rules.extend([(rule, RULES_FILE) for rule in rules_data.get("rules", [])])
            except Exception as e:
                print(f"\nError reading declarative policies from '{RULES_FILE}': {e}")
                
        if os.path.exists(RULES_DIR) and os.path.isdir(RULES_DIR):
            import glob
            for file_path in glob.glob(os.path.join(RULES_DIR, "*.json")):
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    all_rules.extend([(rule, os.path.basename(file_path)) for rule in data.get("rules", [])])
                except Exception as e:
                    print(f"\nError reading declarative policies from folder '{RULES_DIR}': {e}")

        if all_rules:
            print("\nDeclarative Rules Loaded:")
            print("=" * 80)
            for idx, (rule, source) in enumerate(all_rules, 1):
                print(f"Rule #{idx}: {rule.get('name', 'Unnamed')} (Source: {source})")
                print(f"  Condition: {rule.get('condition')}")
                print(f"  Action:    {rule.get('action')}")
                print(f"  Reason:    {rule.get('reason')}")
                print("=" * 80)
        print()

    elif args.command == "export":
        if not os.path.exists(args.db):
            print(f"Error: Ledger file {args.db} not found.")
            sys.exit(1)
            
        ledger = BitemporalLedger(db_path=args.db)
        if args.as_of:
            history = ledger.get_history_as_of(args.as_of)
        else:
            history = ledger.get_history()
            
        report_content = ""
        if args.format == "csv":
            import io
            import csv
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Namespace", "Intent ID", "Actor Agent", "Status", "Reason Codes", "Timestamp", "Previous Hash", "Record Hash"])
            for r in history:
                writer.writerow([
                    r.get("namespace", "default"),
                    r["intent_id"],
                    r["actor_agent"],
                    r["status"],
                    ", ".join(r["reason_codes"]) if isinstance(r["reason_codes"], list) else str(r["reason_codes"]),
                    r["timestamp"],
                    r["previous_hash"],
                    r["record_hash"]
                ])
            report_content = output.getvalue()
            
        elif args.format == "markdown":
            import time
            md = []
            md.append("# DASC Compliance Security Audit Report")
            md.append(f"\n* **Generated**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
            if args.as_of:
                md.append(f"* **Bitemporal Cutoff (As Of)**: {args.as_of}")
            md.append(f"* **Ledger Integrity Check**: {'PASS' if ledger.verify_integrity() else 'FAIL'}")
            
            md.append("\n## Audit Trail Summary")
            total = len(history)
            commits = len([h for h in history if h["status"] == "COMMIT"])
            rejections = len([h for h in history if h["status"] == "REJECT"])
            escalations = len([h for h in history if h["status"] == "ESCALATE"])
            
            md.append(f"* **Total Evaluated Intents**: {total}")
            md.append(f"* **Total Commits**:           {commits}")
            md.append(f"* **Total Rejections**:        {rejections}")
            md.append(f"* **Total Escalations**:       {escalations}")
            
            md.append("\n## Ledger Records")
            md.append("| Timestamp | Intent ID | Agent | Status | Reasons | Record Hash |")
            md.append("| --- | --- | --- | --- | --- | --- |")
            for r in history:
                reasons_str = ", ".join(r["reason_codes"]) if isinstance(r["reason_codes"], list) else str(r["reason_codes"])
                md.append(f"| {r['timestamp']} | `{r['intent_id']}` | `{r['actor_agent']}` | **{r['status']}** | {reasons_str or 'None'} | `{r['record_hash'][:8]}` |")
            report_content = "\n".join(md)
            
        else: # default json
            report_content = json.dumps({"history": history}, indent=2)
            
        if args.out:
            try:
                with open(args.out, "w") as f:
                    f.write(report_content)
                print(f"✅ Successfully exported ledger report in {args.format} format to {args.out}")
            except Exception as e:
                print(f"Error writing file: {e}")
                sys.exit(1)
        else:
            print(report_content)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
