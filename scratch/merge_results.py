import json
import os

all_results = []
for i in range(6):
    file_path = f'research/identity/5f2/batch_{i:03d}_results.json'
    if os.path.exists(file_path):
        try:
            with open(file_path) as f:
                data = json.load(f)
                all_results.extend(data)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            # Try to fix JSON if it's broken or markdown wrapped
            with open(file_path) as f:
                content = f.read()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                    all_results.extend(json.loads(content))

with open('research/identity/5f2/model_labels.json', 'w') as f:
    json.dump(all_results, f, indent=2)

print(f"Merged {len(all_results)} labels.")
