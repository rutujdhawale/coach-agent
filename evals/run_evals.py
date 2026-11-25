"""Lightweight evaluation suite for guardrails, textbook RAG, and optional live ADK runs."""
import argparse
import asyncio
import json
from pathlib import Path
from typing import Dict, List

from app.security.guardrails import check_user_message, sanitize_output
from app.services.rag_service import TextbookRagService


def run_offline_evals(cases_path: str = "evals/cases.json") -> Dict[str, object]:
    cases: List[dict] = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    rag = TextbookRagService()
    results = []

    for case in cases:
        cat = case["category"]
        passed = False
        detail = ""

        if cat in ("guardrail_block", "guardrail_allow"):
            allowed, reason = check_user_message(case["input"])
            passed = allowed == case["expected_allowed"]
            detail = f"allowed={allowed}, reason={reason}"
        elif cat == "rag_retrieval":
            hits = rag.retrieve(query=case["query"], topic=case["topic"], top_k=3)
            expected = case["expected_source_substring"]
            passed = any(expected in h["source"] for h in hits)
            detail = f"hits={[h['source'] for h in hits]}"

        results.append({"id": case["id"], "category": cat, "passed": passed, "detail": detail})

    # Verify secret redaction
    sample_leak = "gsk_1234567890abcdefghijklmnop mongodb+srv://user:pass@cluster.mongodb.net/db"
    redacted = sanitize_output(sample_leak)
    redact_ok = "gsk_" not in redacted and "mongodb+srv://" not in redacted
    results.append({"id": "secret_redaction", "category": "guardrail_output", "passed": redact_ok, "detail": redacted})

    passed_count = sum(1 for r in results if r["passed"])
    return {
        "total": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "pass_rate": round(passed_count / len(results), 4) if results else 1.0,
        "results": results,
    }


async def run_live_eval() -> Dict[str, object]:
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/coach/chat",
            json={
                "student_id": "lk_g7_kavindu",
                "message": "What are my weak topics and give me 1 Fractions & Algebra question?",
            },
        )
        body = resp.json().get("response", "")
        passed = resp.status_code == 200 and "Fractions" in body
        return {"id": "live_lk_g7_coach", "status": resp.status_code, "passed": passed, "preview": body[:180]}


def main():
    parser = argparse.ArgumentParser(description="Run Examblue agent evaluations.")
    parser.add_argument("--live", action="store_true", help="Also run a live LLM end-to-end eval.")
    args = parser.parse_args()

    summary = run_offline_evals()
    print(json.dumps(summary, indent=2))
    if args.live:
        live_res = asyncio.run(run_live_eval())
        print("\nLive Eval:\n", json.dumps(live_res, indent=2))
        if not live_res["passed"]:
            raise SystemExit(1)

    if summary["failed"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
