import sys, re

with open(r'reports\test_eval_20260409_012318.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Extract scenario blocks
scenarios = text.split("Scenario ")
for s in scenarios:
    if "Failed" in s or "Failure" in s or "FAIL" in s or "❌" in s:
        # Find steps inside this scenario that contain failure marks
        steps = re.findall(r'<div class="step.*?>(.*?)</div>', s, re.DOTALL | re.IGNORECASE)
        if not steps:
            steps = s.split("<td")
            
        print("-------")
        for st in steps:
            if "FAIL" in st.upper() or "❌" in st:
                # Strip HTML
                clean = re.sub(r'<[^>]+>', ' ', st)
                clean = re.sub(r'\s+', ' ', clean).strip()
                print(clean)
