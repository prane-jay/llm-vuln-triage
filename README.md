# LLM Assisted Vulnerability Triage
This project scans OWASP Juice Shop with Semgrep, then asks a small local LLM to triage each finding and measuring its answers against a hand labelled answer key. 

> **Note:** all testing was done on a deliberately vulnerable app, OWASP Juice Shop, running locally on my own machine. Nothing was tested against real websites

## Summary
- Semgrep produced 14 findings. I labelled 12 as real and 2 as false positives.
- `qwen2.5-coder:7b` (local) matched my labels on 11/74 (78.6%) in both runs. Labelling everything "real" would have scored 12/14(85.7%), so the model did not beat that baseline.
- At temperature 0, the model called 13/14 findings real and caught 0/2 false positives.
- Default sampling gave different mistakes on the same input, proving that a single run is not a stable measurement

## Setup
- **Target:** OWASP Juice Shop source clones from GitHub (commit `717f5ef`)
- **Scanner:** Semgrep 1.183.0, ruleset `p/owasp-top-ten`
- **Model: ** `qwen2.5-coder:7b` (4-bit quantised), served locally by Ollama
- Hardware: 16 GB Ram, CPU Only (for llm), Linux Mint

## Method
1. Scanned Juice Shop with `semgrep scan --config p/owasp-top-ten --json --output results.json routes lib models server.ts`, which gave 14 findings from 6 rules.
2. Labelled every finding by hand as `real` or `false_positive`, with a one-line reason on `labels.csv`. Note: #6 and #10 were judgement calls
3. For each finding, `triage.py` sends the model the rule name, the file, along with lines before and after for context. The flagged line is marked with `>>`. the model must answer in JSON, a verdict and a short reason.
4. Ran the same prompt twice: **Run 1** with default sampling, and **Run 2** with `temperature: 0, seed: 42`, the official run
5. `compare.py` scores each run against the handwritten `labels.csv`.

## Results

| Metric                                   | Run 1 (default sampling) | Run 2 (temperature 0) |
| ---------------------------------------- | ------------------------ | ------------------------ |
|                                          |                          |                          |
| Accuracy                                 | 11/14 (78.6%)            | 11/14 (78.6%)            |
| "Always real" baseline                   | 12/14 (85.7%)            | 12/14 (85.7%)            |
| Real findings kept as real               | 10/12                    | 11/12                    |
| False positives caught                   | 1/2                      | 0/2                      |
| Its false_positive calls that were right | 1/3                      | 0/1                      |
| Wrong findings                           | #1, #5, #10              | #1, #10, #12             |

Accuracy alone is misleading in this because 12 of the 14 findings are real. The more important number is how many false positives from semgrep the model catches. This is the main point of the triage: 1/2 in Run 1 and 0/2 in Run 2. 

## Conclusion
On this sample, a small 7B model was not reliable enough to filter Semgrep findings. It kept nearly everything as real, so it removed almost no noise, and its few false positive calls mostly wrong. It it better to treat it as a first pass assistant whose verdicts need a human, or stronger LLM to verify it's findings rather than an automatic filter. The failures, the missing context, confident wrong claims about libraries, inconsistent answers between runs, point to what a better triage pipeline would need. 

## Example: Finding #12 (intentionally public folder) 
Finding 12 is a false positive in my labels: `server.ts` line 294 lists the `.well-known` folder on purpose, and nothing sensitive is in it. In Run 1 the model got this right, noting that the folder normally holds public files such as `robots.txt`. In Run 2, with the same prompt and code, it called the finding **real** and its merged `.well-known` together with the `encryptionkeys` and `logs` directories flagged on the nearby lines of the file. Therefore, the correct call in Run 1 looks like luck, since the model did not reliably separate the folders. 

## Where the LLM fails
1. **Confident wrong claims about libraries.** In Run 1 the model said #5 (SQL injection) was safe because Sequelize "uses parameterized queries under the hood", which is actually false when the query string is built by interpolation.
2. **Generic reasoning.** For the directory listing findings (#10 through #14) the explanations were close to boilerplate: "can expose sensitive information if not properly secured". This means nothing, and would require a second look to verify and fix regardless of whether it is true or not.
3. **Right verdict for the wrong reason.** By my hand made answer key, several correct "real" verdicts were stated for the wrong reason. For example, the model described #2 and #3 as "missing sanitization" while my labels say the real problems are "an allowlist checked before a null byte is cut" (#2) and "no allowlist at all" (#3)

## Limitations
- Only 14 findings from one app, one model, one prompt, and one run per setting. The results are illustrative, not statistically meaningful.
- I wrote the answer key myself.
- Temperature 0 was run once, so I have not verified that it reproduces exactly
- Juice Shop is widely documented, so the model may have seen it in training, which could effect the results
- Semgrep's free output does not include code snippets, so `triage.py` reads the surrounding code from the juice shop files itself

## Reproduce 

```bash
# 1. Install Ollama (https://ollama.com) and pull the model
ollama pull qwen2.5-coder:7b

# 2. Python environment
python3 -m venv .venv && source .venv/bin/activate
pip install semgrep requests

# 3. Get the target app (expected at ~/juice-shop)
git clone https://github.com/juice-shop/juice-shop.git ~/juice-shop

# 4. Run the triage, then score it
python3 triage.py
python3 compare.py verdicts_temp0.csv
```
`results.json` (the Semgrep output) is included so you do not need to re run the scan. 

## Files
- `triage.py`: builds the prompt for each finding, queries the local model, saves verdicts
- `compare.py`: scores a verdicts file against the labels
- `list_findings.py`: prints the Semgrep findings
- `labels.csv`: my hand labelled answer key for semgrep findings
- `results.json`: semgrep output
- `verdicts_temp0.csv`: run 2 (temperature 0, official)
- `verdicts_default_sampling.csv`: run 1 (default sampling)

## Possible next steps 
- Try a larger model or few shot examples, and add a formal reasoning correctness score
- Test other vulnerable apps for a bigger sample

