import os
from datetime import datetime
from typing import Any

import jsonlines


class ComplianceTracer:
    """
    Traces every interaction through the Compliance Engine for the Attestation Report.
    """

    def __init__(self, run_id: str | None = None):
        if not run_id:
            run_id = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

        self.run_dir = f"reports/{run_id}"
        os.makedirs(self.run_dir, exist_ok=True)
        self.trace_file = os.path.join(self.run_dir, "compliance_traces.jsonl")
        self.stats = {"total_runs": 0, "failed_compliance": 0, "rule_counts": {}}

    def log_interaction(self, patient_id: str, visit_id: str, result: Any):
        self.stats["total_runs"] += 1
        if not result.is_safe_to_file:
            self.stats["failed_compliance"] += 1

        for alert in result.alerts:
            current_count = self.stats["rule_counts"].get(alert.rule_id, 0)
            self.stats["rule_counts"][alert.rule_id] = current_count + 1

        entry = {
            "timestamp": datetime.now().isoformat(),
            "patient_id": patient_id,
            "visit_id": visit_id,
            "is_safe": result.is_safe_to_file,
            "score": result.score,
            "alerts": [a.model_dump() for a in result.alerts],
        }

        with jsonlines.open(self.trace_file, mode="a") as writer:
            writer.write(entry)

    def generate_html_report(self):
        report_path = os.path.join(self.run_dir, "attestation_report.html")

        rule_stats = "".join(
            [
                f"<li><strong>{rule}:</strong> {count} hits</li>"
                for rule, count in self.stats["rule_counts"].items()
            ]
        )

        total = self.stats["total_runs"]
        failed = self.stats["failed_compliance"]
        rate = ((total - failed) / total * 100) if total > 0 else 0.0

        html_content = f"""
        <html>
        <head>
            <title>Clinical Guardrails Attestation Report</title>
            <style>
                body {{
                    font-family: sans-serif;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 40px auto;
                    padding: 20px;
                }}
                .summary {{
                    background: #f4f4f4;
                    padding: 20px;
                    border-radius: 8px;
                }}
                .alert-card {{
                    border-left: 5px solid red;
                    background: #fff5f5;
                    padding: 10px;
                    margin: 10px 0;
                }}
                .success-card {{
                    border-left: 5px solid green;
                    background: #f5fff5;
                    padding: 10px;
                    margin: 10px 0;
                }}
                h2 {{ color: #2c3e50; }}
            </style>
        </head>
        <body>
            <h1>QA Attestation: Clinical Guardrails</h1>
            <div class="summary">
                <h2>Executive Summary</h2>
                <p><strong>Total Scenarios Verified:</strong> {total}</p>
                <p><strong>Compliance Failures Detected:</strong> {failed}</p>
                <p><strong>Compliance Rate:</strong> {rate:.1f}%</p>
            </div>

            <h2>Rule Violation Statistics</h2>
            <ul>
                {rule_stats}
            </ul>

            <p><i>This report was automatically generated as
            evidence of deterministic safety guardrails.</i></p>
        </body>
        </html>
        """

        with open(report_path, "w") as f:
            f.write(html_content)
        return report_path
