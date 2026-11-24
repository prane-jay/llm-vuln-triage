# LLM Assisted Vulnerability Triage
This project scans OWASP Juice Shop with Semgrep, then asks a small local LLM to triage each finding and measures its answers against a hand labelled answer key. 

> **Note:** all testing was done on a deliberately vulnerable app, OWASP Juice Shop, running locally on my own machine. Nothing was tested against real websites.

## Summary
- Semgrep produced 14 findings. I labelled 12 as real and 2 as false positives.
- `qwen2.5-coder:7b` (local), given 40 lines of code above each flagged line, matched my labels on 12/14 (85.7%). Labelling everything "real" also scores 12/14 (85.7%), so the model did not beat that baseline.
- It called all 14 findings real and caught 0 of the 2 false positives, so it removed no noise.
- My first version used only 15 lines of context and scored 11/14: it missed #1 because the hard coded key was outside the window. Widening the window fixed that.
- Until I set temperature of the model to 0, the same prompt gave different mistakes on different runs, showing that a single default sampling run is not a stable measurement

## Setup
- **Target:** OWASP Juice Shop source cloned from GitHub (commit `717f5ef`)
- **Scanner:** Semgrep 1.183.0, ruleset `p/owasp-top-ten`
- **Model:** `qwen2.5-coder:7b` (4-bit quantised), served locally by Ollama
- **Hardware:** 16 GB Ram, CPU Only (for llm), Linux Mint

## Method
1. Scanned Juice Shop with `semgrep scan --config p/owasp-top-ten --json --output results.json routes lib models server.ts`, which gave 14 findings from 6 rules.
2. Labelled every finding by hand as `real` or `false_positive`, with a one-line reason on `labels.csv`. Note: #6 and #10 were judgement calls
3. For each finding, `triage.py` sends the model the rule name, the file, and the code around the flagged line. The window size is an option; my results use 40 lines above and 15 below. The flagged line is marked with `>>`. the model must answer in JSON, a verdict and a short reason.
4. Ran the model at `temperature: 0, seed: 42` so results are repeatable. My first version used a 15-line window; after seeing it miss #1, I widened it to 40 lines (`python3 triage.py 40`). Because I chose that after seeing the failures, the improvement is not a clean held-out result.
5. `compare.py` scores the verdicts against the handwritten `labels.csv`.

## Results

| ---------------------------------------- | --------------------------- |
| Metric                                   | 40 lines of context (final) |
| Accuracy                                 | 12/14 (85.7%)               |
| "Always real" baseline                   | 12/14 (85.7%)               |
| Real findings kept as real               | 12/12                       |
| False positives caught                   | 0/2                         |
| Its false_positive calls that were right | 0/0 (made none)             |
| Wrong findings                           | #10, #12                    |

Accuracy equals the baseline because the model called every finding real, so it removed no noise. The more significant number here is how many false positives it catches, which is the point of the triage: 0 of 2. For comparison, my first version with 15 lines of context scored 11/14 and also caught 0 of 2 (it wrongly called #1 a false positive due to lack of appropriate context)

## Conclusion
On this sample, a small 7B model was not reliable enough to filter Semgrep findings. It kept nearly everything as real, so it removed almost no noise, and it caught neither of the 2 false positives. It it better to treat it as a first pass assistant whose verdicts need a human, or stronger LLM to verify it's findings rather than an automatic filter. The failures, the missing context, confident wrong claims about libraries, inconsistent answers between runs, point to what a better triage pipeline would need. 

## Example: Finding #1 (hard-coded JWT key) 

Semgrep flagged line 54 of `lib/insecurity.ts`, but the hard coded key is on line 21. In my first version the prompt covered lines 39-69, so the model never saw the key and called the finding a false positive, saying that a private key for JWT signing is a secure practice. With 40 lines above (lines 14-69) it saw the key and answered correctly. It declared it was real, because the code containes a hard coded RSA private key. That confirms the failure was because of missing context, not the model's judgement.

## Where the LLM fails
1. **Confident wrong claims about libraries.** In an earlier run the model said #5 (SQL injection) was safe because Sequelize "uses parameterized queries under the hood", which is actually false when the query string is built by interpolation.
2. **Generic reasoning.** For the directory listing findings (#10 through #14) the explanations were close to boilerplate: "can expose sensitive information if not properly secured". This means nothing, and would require a second look to verify and fix regardless of whether it is true or not.
3. **Right verdict for the wrong reason.** By my hand made answer key, several correct "real" verdicts were stated for the wrong reason. For example, the model described #2 and #3 as "missing sanitization" while my labels say the real problems are "an allowlist checked before a null byte is cut" (#2) and "no allowlist at all" (#3)
 4. **Instability.** Without a fixed temperature the same prompt and code gave different answers across runs (#5 and #12 each flipped), so the model's few correct false-positive calls look like luck. The raw results are in `verdicts_default_sampling.csv`.

## Limitations
- Only 14 findings from one app, one model, one prompt, and one run per setting. The results are illustrative, not statistically meaningful.
- I wrote the answer key myself.
- Temperature 0 was run once, so I have not verified that it reproduces exactly
- Juice Shop is widely documented, so the model may have seen it in training, which could effect the results
- Semgrep's free output does not include code snippets, so `triage.py` reads the surrounding code from the juice shop files itself
- The 40 line window was chosen after seeing the 15-line version's failures, so the improvement is not a clean held out result

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
python3 triage.py 40  # outputs verdicts_temp0_ctx40.csv
python3 compare.py verdicts_temp0_ctx40.csv
```
`results.json` (the Semgrep output) is included so you do not need to re run the scan. 

## Files
- `triage.py`: builds the prompt for each finding, queries the local model, saves verdicts (optional argument: lines of context above the flagged line)
- `compare.py`: scores a verdicts file against the labels
- `list_findings.py`: prints the Semgrep findings
- `labels.csv`: my hand labelled answer key for semgrep findings
- `results.json`: semgrep output
- `verdicts_temp0_ctx40.csv`: final results (temperature 0, 40 lintes of context) 
- `verdicts_temp0.csv` and `verdicts_default_sampling.csv`: earlier runs (15 lines of context) 

## Possible next steps 
- Try a larger model or few shot examples, and add a formal reasoning correctness score
- Test other vulnerable apps for a bigger sample
- Give each directory listing its own non overlapping context, so #10 through #14 are judged separately 

