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

    # Calculate Hash
    hash_parser = subparsers.add_parser("hash", help="Calculate SHA-256 hash for OCC")
    hash_parser.add_argument("file", help="File to hash")

    # Verify Intent
    verify_parser = subparsers.add_parser("verify", help="Manually verify an intent JSON file")
    verify_parser.add_argument("intent_file", help="Path to intent.json")
    verify_parser.add_argument("--state", help="JSON string of current state versions (optional)")

    args = parser.parse_args()

    if args.command == "inspect":
        if not os.path.exists(args.db):
            print(f"Error: Ledger file {args.db} not found.")
            return
        
        ledger = BitemporalLedger(db_path=args.db)
        history = ledger.get_history()
        
        print(f"\n{'TIMESTAMP':<25} | {'INTENT_ID':<15} | {'STATUS':<10} | {'AGENT':<15}")
        print("-" * 75)
        for entry in history[:args.limit]:
            print(f"{entry['timestamp']:<25} | {entry['intent_id']:<15} | {entry['status']:<10} | {entry['actor_agent']:<15}")

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

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
