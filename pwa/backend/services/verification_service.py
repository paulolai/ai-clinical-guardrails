# pwa/backend/services/verification_service.py
"""Clinical verification service for extracted data."""

from typing import Any

# Known medications list (simplified - use RxNorm in production)
KNOWN_MEDICATIONS = {
    "metformin",
    "insulin",
    "lisinopril",
    "atorvastatin",
    "amlodipine",
    "albuterol",
    "omeprazole",
    "gabapentin",
}

# Known conditions (simplified - use ICD-10 in production)
KNOWN_CONDITIONS = {"diabetes", "hypertension", "asthma", "depression", "anxiety", "arthritis", "copd", "heart failure"}


class VerificationService:
    """Verifies extracted clinical data for safety."""

    def __init__(self) -> None:
        self.checks: list[str] = []

    def verify(self, extracted_data: dict[str, Any]) -> dict[str, Any]:
        """Verify extracted data and return results.

        Returns:
            dict with: passed (bool), score (float), issues (list)
        """
        issues = []
        score = 1.0

        # Check 1: Confidence threshold
        confidence = extracted_data.get("confidence", 0.0)
        if confidence < 0.5:
            issues.append(f"Low confidence: {confidence}")
            score -= 0.3

        # Check 2: Medication names
        for med in extracted_data.get("medications", []):
            name = med.get("name", "").lower()
            if name and name not in KNOWN_MEDICATIONS:
                issues.append(f"Unknown medication: {name}")
                score -= 0.1

        # Check 3: Dosage format
        for med in extracted_data.get("medications", []):
            dosage = med.get("dosage", "")
            if dosage and not any(c.isdigit() for c in dosage):
                issues.append(f"Invalid dosage format: {dosage}")
                score -= 0.1

        # Check 4: Conditions
        for condition in extracted_data.get("conditions", []):
            condition_lower = condition.lower()
            if condition_lower not in KNOWN_CONDITIONS:
                issues.append(f"Unknown condition: {condition}")
                score -= 0.05

        # Normalize score
        score = max(0.0, min(1.0, score))

        return {
            "passed": score >= 0.7 and len(issues) < 3,
            "score": score,
            "issues": issues,
            "checks_performed": ["confidence_threshold", "medication_names", "dosage_format", "condition_names"],
        }
