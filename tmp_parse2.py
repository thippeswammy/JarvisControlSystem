import re

with open(r'reports\test_eval_20260409_012318.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Extract scenario blocks
scenarios = re.findall(r'<div class="scenario(.*?)(?=<div class="scenario|</body>)', text, re.DOTALL)
output = []
for s in scenarios:
    if "Failed" in s or "❌" in s or "class=\"status status-fail\"" in s:
        # get scenario name
        name_match = re.search(r'<h2>(.*?)</h2>', s)
        scenario_name = name_match.group(1).strip() if name_match else "Unknown"
        output.append(f"SCENARIO FAILED: {scenario_name}")
        
        # find failed steps
        steps = re.findall(r'<div class="step(.*?)</div>\s*</div>\s*</div>', s, re.DOTALL)
        if not steps:
            steps = s.split('class="step')
        for st in steps:
            if "status-fail" in st or "❌" in st or "FAILED" in st:
                clean = re.sub(r'<[^>]+>', ' ', st)
                clean = re.sub(r'\s+', ' ', clean).strip()
                output.append("  FAILED STEP: " + clean[:200])

with open("failed_scenarios.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))
print("Extraction complete. Check failed_scenarios.txt")
