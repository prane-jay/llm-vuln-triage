import csv
import json
import os
import requests

JUICE_SHOP = os.path.expanduser("~/juice-shop")
RESULTS = "results.json"   
URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5-coder:7b"


def get_context(path, line, before=15, after=15):
    """Return the code around the flagged line, where the flagged is the line marked >>"""
    with open(os.path.join(JUICE_SHOP, path)) as f:
        lines = f.read().splitlines()
    start = max(0, line - 1 - before)
    stop = min(len(lines), line + after)
    out = []
    for i in range(start, stop):
        marker = ">>" if i == line - 1 else "  "
        out.append(f"{marker} {i + 1}: {lines[i]}")
    return "\n".join(out)


def build_prompt(finding):
    rule = finding["check_id"]
    path = finding["path"]
    line = finding["start"]["line"]
    code = get_context(path, line)
    return f"""Act as a security code reviewer. Semgrep flagged the code below.
Decide whether this is a real vulnerability or a false positive.

Rule: {rule}
File: {path}
The flagged line is marked with >>

Code:
{code}

Answer with JSON only, in this format:
{{"verdict": "real" or "false_positive", "reason": "one or two sentences"}}"""


def ask(prompt):
    payload = {"model": MODEL, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0, "seed":42}}
    r = requests.post(URL, json=payload, timeout=600)
    return r.json()["response"]


if __name__ == "__main__":
    with open(RESULTS) as f:
        findings = json.load(f)["results"]

    rows = []
    for number, finding in enumerate(findings, start=1):
        print(f"Finding {number}/{len(findings)} ...", flush=True)
        answer = ask(build_prompt(finding))
        try:
            parsed = json.loads(answer)
            verdict = str(parsed["verdict"]).strip().lower()
            reason = parsed["reason"]
        except (json.JSONDecodeError, KeyError):
            verdict = "error"
            reason = answer
        print(f"  -> {verdict}")
        rows.append({
            "number": number,
            "rule": finding["check_id"].split(".")[-1],
            "file": finding["path"],
            "line": finding["start"]["line"],
            "llm_verdict": verdict,
            "llm_reason": reason,
        })

    with open("verdicts_temp0.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print("Saved verdicts_temp0.csv")
