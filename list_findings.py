import json

with open("results.json") as f:
	data = json.load(f)

findings = data["results"]

for n, finding in enumerate(findings, start = 1):
	rule = finding["check_id"]
	path = finding["path"]
	line = finding["start"]["line"]
	print(f"{n}. {rule} | {path} | line {line}")

