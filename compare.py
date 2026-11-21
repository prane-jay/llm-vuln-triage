import csv
import sys

verdict_file = sys.argv[1] if len(sys.argv) > 1 else "verdicts_temp0.csv"


def load(path):
    """Read a CSV into a dict keyed by finding number."""
    with open(path, newline="") as f:
        return {int(row["number"]): row for row in csv.DictReader(f)}


labels = load("labels.csv")
verdicts = load(verdict_file)

total = len(labels)
correct = 0
real_total = real_kept = 0
fp_total = fp_caught = 0
fp_calls = fp_calls_right = 0
misses = []

for number, lab in labels.items():
    truth = lab["label"]
    guess = verdicts[number]["llm_verdict"]

    if truth == "real":
        real_total += 1
        if guess == "real":
            real_kept += 1
    else:
        fp_total += 1
        if guess == "false_positive":
            fp_caught += 1

    if guess == "false_positive":
        fp_calls += 1
        if truth == "false_positive":
            fp_calls_right += 1

    if guess == truth:
        correct += 1
    else:
        misses.append(number)

print(f"File: {verdict_file}")
print(f"Accuracy:                    {correct}/{total} ({100 * correct / total:.1f}%)")
print(f"'Always real' baseline:      {real_total}/{total} ({100 * real_total / total:.1f}%)")
print(f"Real findings kept as real:  {real_kept}/{real_total}")
print(f"False positives caught:      {fp_caught}/{fp_total}")
print(f"Its FP calls that were right: {fp_calls_right}/{fp_calls}")
print()
print("Misses:")
for number in misses:
    lab = labels[number]
    ver = verdicts[number]
    print(f"  #{number} {lab['file']}:{lab['line']}")
    print(f"     your label: {lab['label']} - {lab['reason']}")
    print(f"     model:      {ver['llm_verdict']} - {ver['llm_reason'][:150]}")
