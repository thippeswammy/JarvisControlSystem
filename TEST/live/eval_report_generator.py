import os
import io
import base64
from datetime import datetime

class VisualReportGenerator:
    def __init__(self, report_dir="reports"):
        self.report_dir = report_dir
        os.makedirs(self.report_dir, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.html_file = os.path.join(self.report_dir, f"test_eval_{self.timestamp}.html")
        
        self.html_content = [
            "<html><head><title>Jarvis Visual Eval Report</title>",
            "<style>",
            "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #1e1e1e; color: #eee; margin: 20px; }",
            ".scenario { border: 1px solid #444; margin-top: 20px; padding: 15px; border-radius: 8px; background: #252526; }",
            ".step { margin-bottom: 20px; padding: 15px; border-bottom: 1px solid #444; background: #1e1e1e; border-radius: 6px; }",
            ".step-title { font-weight: bold; margin-bottom: 10px; font-size: 1.1em; }",
            ".pass { color: #4CAF50; font-weight: bold; }",
            ".fail { color: #f44336; font-weight: bold; }",
            ".cmd { background: #000; padding: 6px 12px; border-radius: 6px; font-family: 'Consolas', monospace; color: #d4d4d4; }",
            ".images { display: flex; gap: 15px; margin-top: 15px; }",
            ".img-container { text-align: center; font-size: 0.9em; color: #aaa; background: #2d2d30; padding: 10px; border-radius: 6px; }",
            ".img-container img { max-width: 450px; border: 1px solid #555; border-radius: 4px; display: block; margin-top: 5px; cursor: pointer; transition: transform 0.2s; }",
            ".img-container img:hover { transform: scale(1.02); }",
            "</style></head><body>",
            "<h1>Jarvis Visual Evaluation Report</h1>"
        ]

    def _img_to_base64(self, pil_img):
        if not pil_img:
            return ""
        buffered = io.BytesIO()
        # Scale image down slightly to save HTML file size
        pil_img.thumbnail((1280, 720))
        pil_img.save(buffered, format="JPEG", quality=75)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"

    def add_scenario(self, scenario_name, scenario_passed):
        status_class = "pass" if scenario_passed else "fail"
        status_txt = "PASS" if scenario_passed else "FAIL"
        self.html_content.append(f"<div class='scenario'>")
        self.html_content.append(f"<h2>Scenario: {scenario_name} - <span class='{status_class}'>{status_txt}</span></h2>")

    def add_step(self, command, desc, expect_success, expect_visual, success, message, img_before, img_after):
        # Determine actual status considering expectation
        is_pass = (success == expect_success)
        status_class = "pass" if is_pass else "fail"
        status_txt = "PASS" if is_pass else "FAIL"
        
        self.html_content.append(f"<div class='step'>")
        self.html_content.append(f"<div class='step-title'><span class='{status_class}'>[{status_txt}]</span> <span class='cmd'>{command}</span></div>")
        self.html_content.append(f"<div style='color: #bbb; margin-bottom: 8px;'>Description: {desc}</div>")
        
        exp_text = f"Expected Success: {expect_success}"
        if expect_visual:
            exp_text += " | Expected Visual Change: True"
        self.html_content.append(f"<div style='color: #888; font-size: 0.9em; margin-bottom: 8px;'>{exp_text}</div>")
        
        if message:
            self.html_content.append(f"<div style='margin-bottom: 8px;'>Result Message: <em>{message}</em></div>")
            
        if img_before or img_after:
            self.html_content.append("<div class='images'>")
            if img_before:
                b64 = self._img_to_base64(img_before)
                self.html_content.append(f"<div class='img-container'><div>Before</div><a href='{b64}' target='_blank'><img src='{b64}'></a></div>")
            if img_after:
                b64 = self._img_to_base64(img_after)
                self.html_content.append(f"<div class='img-container'><div>After</div><a href='{b64}' target='_blank'><img src='{b64}'></a></div>")
            self.html_content.append("</div>")
            
        self.html_content.append("</div>")

    def end_scenario(self):
        self.html_content.append("</div>")

    def save(self):
        self.html_content.append("</body></html>")
        with open(self.html_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(self.html_content))
        return self.html_file
