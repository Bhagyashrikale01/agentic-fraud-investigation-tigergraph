import json
import os

INPUT = "final_20_case_outputs.json"
OUTPUT_DIR = "cases"

os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(INPUT, "r", encoding="utf-8") as f:
    results = json.load(f)

for result in results:
    case_id = result["case"]["case_id"]

    output_file = os.path.join(
        OUTPUT_DIR,
        f"{case_id}.json"
    )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False
        )

print("Created", len(results), "case files.")

for result in results:
    print(result["case"]["case_id"])
