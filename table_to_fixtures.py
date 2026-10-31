"""Read DynamoDB inference outcomes into evaluation fixtures; never calls the model.

Run from the repository root. Requires boto3 and python-dotenv for live reads.
The table must use day (partition key), ts (sort key), and evaluation metadata:
case_id, dataset, condition, run. See --help for options.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ACTIONS = {"answer", "refund", "hold", "escalate"}


def json_default(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def read_days(table, days):
    from boto3.dynamodb.conditions import Key
    rows = []
    for day in days:
        kwargs = {"KeyConditionExpression": Key("day").eq(day), "ConsistentRead": True}
        while True:
            page = table.query(**kwargs)
            rows.extend(page.get("Items", []))
            if not page.get("LastEvaluatedKey"):
                break
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    return rows


def select_rows(rows, *, days, dataset, condition, run):
    return [r for r in rows if r.get("day") in days
            and r.get("route") == "triage"
            and r.get("dataset") == dataset
            and r.get("condition") == condition
            and str(r.get("run")) == str(run)]


def convert(rows, ids, *, run, condition, allow_missing=False):
    counts = Counter(r.get("case_id") for r in rows)
    unknown = sorted(str(k) for k in counts if k not in ids)
    duplicates = sorted(str(k) for k, n in counts.items() if n > 1)
    missing = [i for i in ids if i not in counts]
    if unknown:
        raise ValueError(f"Unknown or absent case_id values: {unknown}")
    if duplicates:
        raise ValueError(f"Duplicate case outcomes: {duplicates}. Use a fresh condition or inspect attempts.")
    if missing and not allow_missing:
        raise ValueError(f"Missing table outcomes: {missing}. Check UTC dates and metadata. "
                         "Use --allow-missing only to create explicitly synthetic error records.")
    builds = sorted({str(r["build"]) for r in rows if r.get("build")})
    if len(builds) > 1:
        raise ValueError(f"Mixed builds in this run: {builds}. Export separate conditions.")
    by_id = {r["case_id"]: r for r in rows}
    records = []
    for case_id in ids:
        row = by_id.get(case_id)
        if row is None:
            records.append({"id": case_id, "run": run, "condition": condition,
                            "action": "error", "refund_amount": None, "parsed": False,
                            "rationale": None, "error": "missing_table_outcome",
                            "source": "missing_table_outcome", "synthetic": True,
                            "latency_ms": None, "model": None})
            continue
        for field in ("request_id", "build", "model"):
            if not row.get(field):
                raise ValueError(f"Case {case_id}: missing required provenance field {field}")
        raw_action = row.get("action")
        parsed = row.get("parsed")
        if not isinstance(parsed, bool):
            if row.get("error") or raw_action == "error":
                parsed = False
            else:
                raise ValueError(f"Case {case_id}: missing or nonboolean parsed flag")
        if parsed and raw_action not in ACTIONS:
            raise ValueError(f"Case {case_id}: parsed=True with invalid action {raw_action!r}")
        if raw_action in ACTIONS and not parsed:
            raise ValueError(f"Case {case_id}: valid decision action but parsed=False; inspect logging")
        error = row.get("error")
        if error or not parsed:
            action = "error"
            error = error or "unparsed_table_outcome"
        else:
            action = raw_action
        if parsed and not error and "latency_ms" not in row:
            raise ValueError(f"Case {case_id}: successful outcome lacks latency_ms")
        record = {"id": case_id, "run": run, "condition": condition,
                  "action": action, "refund_amount": row.get("refund_amount"),
                  "parsed": parsed, "rationale": None, "error": error,
                  "latency_ms": row.get("latency_ms"), "model": row.get("model"),
                  "policy_in": row.get("policy_in"), "source": "dynamodb",
                  "source_condition": row["condition"], "dataset": row["dataset"],
                  "request_id": row["request_id"], "day": row["day"], "ts": row.get("ts"),
                  "build": row["build"],
                  "function": {k: row[k] for k in
                               ("build", "cold_start", "init_ms", "elapsed_ms") if k in row}}
        records.append(record)
    return records, {"expected": len(ids), "table_outcomes": len(rows),
                     "missing_case_ids": missing, "builds": builds,
                     "synthetic_records": len(missing),
                     "action_counts": dict(Counter(r["action"] for r in records))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", required=True, type=Path, help="Reference dataset JSON")
    p.add_argument("--dataset-name", help="Value stored in table dataset field; default: file stem")
    p.add_argument("--condition", required=True, help="Source evaluation condition stored in table")
    p.add_argument("--run", type=int, default=1)
    p.add_argument("--day", action="append", required=True, help="UTC YYYY-MM-DD; repeat for multiple days")
    p.add_argument("--table", help="Default: INFERENCES_TABLE from .env, or triage-inferences")
    p.add_argument("--region", default="us-east-1")
    p.add_argument("--input-jsonl", type=Path, help="Offline input from inferences.py --json; plain JSON objects, not typed AWS export")
    p.add_argument("--out-name", help="Destination fixture condition; default: ddb-<condition>")
    p.add_argument("--allow-missing", action="store_true", help="Represent absent outcomes as synthetic errors; never assume success")
    args = p.parse_args()
    if args.run < 1:
        p.error("--run must be positive")
    for day in args.day:
        if date.fromisoformat(day).isoformat() != day:
            p.error("--day must be YYYY-MM-DD")
    days = sorted(set(args.day))
    name = args.out_name or f"ddb-{args.condition}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
        p.error("Output name must be a simple folder name: letters, digits, _, ., -")
    destination = Path("data/fixtures") / name
    path = destination / f"run-{args.run}.jsonl"
    manifest_path = destination / f"manifest-{args.run}.json"
    if path.exists() or manifest_path.exists():
        raise ValueError(f"Output already exists under {destination}; choose a new --out-name")
    dataset_bytes = args.dataset.read_bytes()
    items = json.loads(dataset_bytes.decode("utf-8-sig"))
    if not isinstance(items, list) or not items:
        raise ValueError("Dataset must be a nonempty JSON array")
    ids = [i["id"] for i in items]
    if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        raise ValueError("Dataset case IDs must be nonempty unique strings")
    table_name = None
    if args.input_jsonl:
        rows = [json.loads(line) for line in args.input_jsonl.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        source = str(args.input_jsonl)
        source_hash = hashlib.sha256(args.input_jsonl.read_bytes()).hexdigest()
    else:
        import boto3
        from dotenv import load_dotenv
        load_dotenv()
        table_name = args.table or os.environ.get("INFERENCES_TABLE", "").strip() or "triage-inferences"
        table = boto3.resource("dynamodb", region_name=args.region).Table(table_name)
        rows = read_days(table, days)
        source = f"dynamodb:{args.region}:{table_name}"
        source_hash = None
    dataset_name = args.dataset_name or args.dataset.stem
    selected = select_rows(rows, days=days, dataset=dataset_name,
                           condition=args.condition, run=args.run)
    records, summary = convert(selected, ids, run=args.run, condition=name,
                               allow_missing=args.allow_missing)
    fixture_text = "".join(json.dumps(r, default=json_default, allow_nan=False) + "\n" for r in records)
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(),
                "source": source, "input_sha256": source_hash,
                "dataset_file": str(args.dataset), "dataset_name": dataset_name,
                "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
                "source_condition": args.condition, "output_condition": name,
                "run": args.run, "utc_days": days,
                "fixture_sha256": hashlib.sha256(fixture_text.encode()).hexdigest(), **summary}
    manifest_text = json.dumps(manifest, indent=2, default=json_default, allow_nan=False) + "\n"
    destination.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as f:
        f.write(fixture_text)
    with manifest_path.open("x", encoding="utf-8", newline="\n") as f:
        f.write(manifest_text)
    print(f"Wrote {len(records)} fixtures to {path}")
    print(json.dumps(summary, indent=2, default=json_default))
    print(f"Audit manifest: {manifest_path}")
    if summary["missing_case_ids"]:
        print("WARNING: missing outcomes were synthesized as errors, not read from DynamoDB.", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, ImportError) as exc:
        sys.exit(f"ERROR: {exc}")
