import json
import httpx
import time
import sys

API_URL = "http://localhost:8000"


def call_agent(message: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = httpx.post(
                f"{API_URL}/api/chat/sync",
                json={"message": message, "history": [], "session_id": "eval"},
                timeout=60.0,
            )
            text = response.json().get("response", "")
            if text:
                return text
        except Exception:
            pass
        time.sleep(3 * (attempt + 1))
    return ""


def score_case(case: dict, response: str) -> dict:
    response_lower = response.lower()

    if case["category"] == "factual":
        keywords = case.get("expected_answer_contains", [])
        matched = [kw for kw in keywords if kw.lower() in response_lower]
        missed = [kw for kw in keywords if kw.lower() not in response_lower]
        return {
            "pass": len(missed) == 0,
            "matched_keywords": matched,
            "missed_keywords": missed,
        }

    elif case["category"] == "abstain":
        signals = case.get("expected_response_contains", [])
        abstains = any(s.lower() in response_lower for s in signals)
        overclaims = any(
            phrase in response_lower
            for phrase in ["yes, you can", "you should definitely", "i recommend that you"]
        )
        return {
            "pass": abstains and not overclaims,
            "abstains": abstains,
            "overclaims": overclaims,
        }

    elif case["category"] == "citation":
        expected = case.get("expected_source_contains", [])
        if isinstance(expected, str):
            expected = [expected]
        cites_correct = any(src.lower() in response_lower for src in expected)
        return {
            "pass": cites_correct,
            "cites_correct_source": cites_correct,
            "expected_sources": expected,
        }

    return {"pass": False, "error": "Unknown category"}


def run_eval():
    with open("cases.json") as f:
        cases = json.load(f)

    results = []
    print(f"Running {len(cases)} eval cases against {API_URL}\n")

    for i, case in enumerate(cases):
        label = f"[{i+1:02d}/{len(cases)}] {case['id']}"
        print(f"{label} — {case['input'][:60]}...")

        try:
            response = call_agent(case["input"])
            score = score_case(case, response)
        except Exception as e:
            print(f"  ERROR: {e}")
            score = {"pass": False, "error": str(e)}
            response = ""

        status = "PASS ✓" if score["pass"] else "FAIL ✗"
        print(f"  {status}")
        if not score["pass"] and "missed_keywords" in score:
            print(f"  Missing: {score['missed_keywords']}")

        results.append({**case, "response": response[:600], "score": score})
        time.sleep(0.8)

    # Aggregate
    total = len(results)
    passed = sum(1 for r in results if r["score"]["pass"])

    by_category = {}
    for cat in ["factual", "abstain", "citation"]:
        cat_results = [r for r in results if r["category"] == cat]
        cat_passed = sum(1 for r in cat_results if r["score"]["pass"])
        by_category[cat] = {
            "total": len(cat_results),
            "passed": cat_passed,
            "rate": f"{cat_passed}/{len(cat_results)}",
        }

    summary = {
        "overall": {
            "total": total,
            "passed": passed,
            "pct": f"{passed/total*100:.1f}%" if total else "N/A",
        },
        "by_category": by_category,
        "cases": results,
    }

    with open("results.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*50}")
    print(f"EVAL RESULTS")
    print(f"{'='*50}")
    print(f"Overall:  {passed}/{total} ({passed/total*100:.1f}%)")
    for cat, data in by_category.items():
        bar = "█" * data["passed"] + "░" * (data["total"] - data["passed"])
        print(f"{cat.capitalize():10s}: {data['rate']:6s}  {bar}")
    print(f"{'='*50}")
    print(f"Full results → eval/results.json")


if __name__ == "__main__":
    run_eval()
