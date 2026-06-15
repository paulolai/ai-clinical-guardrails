from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st

from src.extraction.models import ExtractedMedication, StructuredExtraction
from src.models import ComplianceSeverity, PatientProfile
from src.protocols.checkers.drug_class_matcher import DRUG_CLASS_MAP
from src.protocols.checkers.duplicate_therapy_checker import DuplicateTherapyChecker
from src.protocols.models import ProtocolConfig, ProtocolRule, ProtocolSeverity


def _make_patient() -> PatientProfile:
    return PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )


def _make_config(rules_dict: dict | None = None) -> ProtocolConfig:
    if rules_dict is None:
        rules_dict = {
            "duplicate_therapy": [
                ProtocolRule(
                    name="Duplicate ACE Inhibitor",
                    checker_type="duplicate_therapy",
                    pattern={"drug_class": "ACE_INHIBITOR", "max_count": 1},
                    severity=ProtocolSeverity.HIGH,
                    message="Multiple ACE inhibitors detected",
                ),
                ProtocolRule(
                    name="Duplicate Statin",
                    checker_type="duplicate_therapy",
                    pattern={"drug_class": "STATIN", "max_count": 1},
                    severity=ProtocolSeverity.HIGH,
                    message="Multiple statins detected",
                ),
            ]
        }
    return ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"duplicate_therapy": {"enabled": True}},
        rules=rules_dict,
    )


# --- Example tests ---


def test_detects_duplicate_ace_inhibitors():
    checker = DuplicateTherapyChecker(_make_config())
    extraction = StructuredExtraction(
        medications=[
            ExtractedMedication(name="lisinopril"),
            ExtractedMedication(name="enalapril"),
        ]
    )
    alerts = checker.check(_make_patient(), extraction)
    assert len(alerts) == 1
    assert alerts[0].severity == ComplianceSeverity.HIGH


def test_no_alert_for_single_ace_inhibitor():
    checker = DuplicateTherapyChecker(_make_config())
    extraction = StructuredExtraction(
        medications=[ExtractedMedication(name="lisinopril")]
    )
    alerts = checker.check(_make_patient(), extraction)
    assert len(alerts) == 0


def test_detects_duplicate_statins():
    checker = DuplicateTherapyChecker(_make_config())
    extraction = StructuredExtraction(
        medications=[
            ExtractedMedication(name="atorvastatin"),
            ExtractedMedication(name="rosuvastatin"),
        ]
    )
    alerts = checker.check(_make_patient(), extraction)
    assert len(alerts) == 1
    assert alerts[0].severity == ComplianceSeverity.HIGH


def test_no_alert_for_medications_in_different_classes():
    checker = DuplicateTherapyChecker(_make_config())
    extraction = StructuredExtraction(
        medications=[
            ExtractedMedication(name="lisinopril"),
            ExtractedMedication(name="atorvastatin"),
        ]
    )
    alerts = checker.check(_make_patient(), extraction)
    assert len(alerts) == 0


def test_empty_extraction_no_alert():
    checker = DuplicateTherapyChecker(_make_config())
    extraction = StructuredExtraction(medications=[])
    alerts = checker.check(_make_patient(), extraction)
    assert len(alerts) == 0


def test_drug_not_in_class_map_no_alert():
    checker = DuplicateTherapyChecker(_make_config())
    extraction = StructuredExtraction(
        medications=[ExtractedMedication(name="metformin")]
    )
    alerts = checker.check(_make_patient(), extraction)
    assert len(alerts) == 0


def test_all_duplicate_classes_detected():
    checker = DuplicateTherapyChecker(_make_config())
    extraction = StructuredExtraction(
        medications=[
            ExtractedMedication(name="lisinopril"),
            ExtractedMedication(name="enalapril"),
            ExtractedMedication(name="atorvastatin"),
            ExtractedMedication(name="rosuvastatin"),
        ]
    )
    alerts = checker.check(_make_patient(), extraction)
    assert len(alerts) == 2


def test_triple_ace_inhibitor_still_one_alert():
    checker = DuplicateTherapyChecker(_make_config())
    extraction = StructuredExtraction(
        medications=[
            ExtractedMedication(name="lisinopril"),
            ExtractedMedication(name="enalapril"),
            ExtractedMedication(name="ramipril"),
        ]
    )
    alerts = checker.check(_make_patient(), extraction)
    assert len(alerts) == 1


# --- Hypothesis strategies ---


DRUG_NAMES_BY_CLASS: dict[str, list[str]] = {}
for _drug, _cls in DRUG_CLASS_MAP.items():
    DRUG_NAMES_BY_CLASS.setdefault(_cls, []).append(_drug)


ALL_DRUG_NAMES = list(DRUG_CLASS_MAP.keys())
ALL_CLASSES = list(DRUG_NAMES_BY_CLASS.keys())


def medication_class_strategy():
    return st.sampled_from(ALL_DRUG_NAMES)


def therapy_config_strategy():
    """Generate a ProtocolConfig with duplicate_therapy rules for random drug classes."""

    def _build_rules(classes_list):
        rules = []
        for cls_name in classes_list:
            rules.append(
                ProtocolRule(
                    name=f"Duplicate {cls_name}",
                    checker_type="duplicate_therapy",
                    pattern={"drug_class": cls_name, "max_count": 1},
                    severity=ProtocolSeverity.HIGH,
                    message=f"Multiple {cls_name} detected",
                )
            )
        return rules

    return st.lists(
        st.sampled_from(ALL_CLASSES),
        min_size=1,
        max_size=len(ALL_CLASSES),
        unique=True,
    ).map(
        lambda cls_list: ProtocolConfig(
            version="1.0",
            settings={},
            checkers={"duplicate_therapy": {"enabled": True}},
            rules={"duplicate_therapy": _build_rules(cls_list)},
        )
    )


# --- Property-based tests ---


@given(
    drug_class=st.sampled_from(ALL_CLASSES),
    count=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=100)
def test_count_matches_actual_duplicates(drug_class: str, count: int):
    drugs = DRUG_NAMES_BY_CLASS[drug_class]
    meds = [ExtractedMedication(name=drugs[i % len(drugs)]) for i in range(count)]
    extraction = StructuredExtraction(medications=meds)

    from src.protocols.checkers.drug_class_matcher import DrugClassMatcher

    actual = DrugClassMatcher().count_by_class(extraction, drug_class)
    assert actual == count


@given(
    drug_class=st.sampled_from(ALL_CLASSES),
    extra=st.integers(min_value=2, max_value=5),
    config=therapy_config_strategy(),
)
@settings(max_examples=100)
def test_class_detection_never_misses(
    drug_class: str, extra: int, config: ProtocolConfig
):
    if drug_class not in {r.pattern["drug_class"] for r in config.rules.get("duplicate_therapy", [])}:
        return

    drugs = DRUG_NAMES_BY_CLASS[drug_class]
    meds = [ExtractedMedication(name=drugs[i % len(drugs)]) for i in range(extra)]
    extraction = StructuredExtraction(medications=meds)

    checker = DuplicateTherapyChecker(config)
    alerts = checker.check(_make_patient(), extraction)

    triggered_classes = set()
    for alert in alerts:
        for rule in config.rules["duplicate_therapy"]:
            if f"DUPLICATE_{rule.pattern['drug_class']}" in alert.rule_id:
                triggered_classes.add(rule.pattern["drug_class"])

    assert drug_class in triggered_classes


@given(config=therapy_config_strategy())
@settings(max_examples=100)
def test_single_class_never_alerts(config: ProtocolConfig):
    rules = config.rules.get("duplicate_therapy", [])
    if not rules:
        return

    meds = []
    for rule in rules:
        cls_name = rule.pattern["drug_class"]
        if cls_name in DRUG_NAMES_BY_CLASS:
            meds.append(ExtractedMedication(name=DRUG_NAMES_BY_CLASS[cls_name][0]))

    extraction = StructuredExtraction(medications=meds)
    checker = DuplicateTherapyChecker(config)
    alerts = checker.check(_make_patient(), extraction)
    assert len(alerts) == 0


@given(drug_names=st.lists(st.sampled_from(ALL_DRUG_NAMES), min_size=1, max_size=10))
@settings(max_examples=100)
def test_alert_count_bounded_by_class_count(drug_names: list[str]):
    config = _make_config()
    extraction = StructuredExtraction(
        medications=[ExtractedMedication(name=n) for n in drug_names]
    )
    checker = DuplicateTherapyChecker(config)
    alerts = checker.check(_make_patient(), extraction)
    assert len(alerts) <= 2
