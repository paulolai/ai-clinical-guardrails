"""Drug class matcher for duplicate therapy detection."""

from src.extraction.models import StructuredExtraction
from src.models import PatientProfile
from src.protocols.matcher import PatternMatcher

# Maps individual drug names to therapeutic classes.
# This is the knowledge base that enables class-level duplicate detection.
DRUG_CLASS_MAP: dict[str, str] = {
    # ACE Inhibitors
    "lisinopril": "ACE_INHIBITOR",
    "enalapril": "ACE_INHIBITOR",
    "ramipril": "ACE_INHIBITOR",
    "perindopril": "ACE_INHIBITOR",
    "captopril": "ACE_INHIBITOR",
    # ARBs
    "losartan": "ARB",
    "valsartan": "ARB",
    "irbesartan": "ARB",
    "candesartan": "ARB",
    # Statins
    "atorvastatin": "STATIN",
    "rosuvastatin": "STATIN",
    "simvastatin": "STATIN",
    "pravastatin": "STATIN",
    # NSAIDs
    "ibuprofen": "NSAID",
    "naproxen": "NSAID",
    "diclofenac": "NSAID",
    "celecoxib": "NSAID",
    # Proton Pump Inhibitors
    "omeprazole": "PPI",
    "esomeprazole": "PPI",
    "pantoprazole": "PPI",
    "lansoprazole": "PPI",
    # Beta Blockers
    "metoprolol": "BETA_BLOCKER",
    "atenolol": "BETA_BLOCKER",
    "propranolol": "BETA_BLOCKER",
    "bisoprolol": "BETA_BLOCKER",
}


class DrugClassMatcher(PatternMatcher):
    """Matches medications by therapeutic class rather than individual names."""

    def matches(
        self,
        patient: PatientProfile,
        extraction: StructuredExtraction,
        pattern: dict[str, str],
    ) -> bool:
        target_class = pattern.get("drug_class", "")
        if not target_class:
            return False

        extracted_classes = set()
        for med in extraction.medications:
            drug_class = DRUG_CLASS_MAP.get(med.name.lower())
            if drug_class:
                extracted_classes.add(drug_class)

        return target_class in extracted_classes

    def count_by_class(
        self,
        extraction: StructuredExtraction,
        drug_class: str,
    ) -> int:
        """Count how many extracted medications belong to the given class."""
        count = 0
        for med in extraction.medications:
            if DRUG_CLASS_MAP.get(med.name.lower()) == drug_class:
                count += 1
        return count
