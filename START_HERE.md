# Start Here

**New to this project?** This file tells you what's been done and what to do next.

---

## Current Status (Quick)

**Phase:** 4.0 - Medical Protocols Complete
**Last Updated:** 2026-02-22
**Status:** ✅ COMPLETE

**What's Done:**
- ✅ Verification engine (compliance checking)
- ✅ **Medical protocols** (drug interactions, allergies, required fields) - **NEW!**
- ✅ FHIR integration
- ✅ Business requirements (15+ docs)
- ✅ Risk analysis (pre-mortem complete)
- ✅ Sample transcripts (10 examples)
- ✅ Extraction module (llm_parser.py, models.py, temporal.py)
- ✅ Multi-provider LLM client (OpenAI, Azure, Synthetic)
- ✅ 114/114 tests passing

**What's Next:**
- ✅ **ALL CORE FEATURES COMPLETE**
- ⏳ Optional: Production deployment
- ⏳ Optional: Additional compliance rules
- ⏳ Optional: Performance optimization

---

## Immediate Next Task

### ✅ Phase 4 Complete: Medical Protocols

**Goal:** Configurable clinical safety rules for drug interactions, allergies, and documentation

**Files:**
- `src/protocols/` - Complete protocol checking system
- `config/medical_protocols.yaml` - Rule configuration
- `cli/protocols.py` - CLI debugging tool

**What's Implemented:**
1. **Drug Interaction Checker** - Detects Warfarin + NSAID, duplicate therapies
2. **Allergy Checker** - Flags penicillin allergy + amoxicillin conflicts
3. **Required Fields Checker** - Validates discharge summary completeness
4. **Protocol Registry** - Orchestrates all checkers
5. **CLI Tool** - Debug and test rules

**Test Results:**
- 46 new protocol tests
- 114 total tests passing
- 2 PBT tests with 100 examples each
- Zero regressions

**Usage:**
```python
from src.protocols.config import load_protocol_config
from src.engine import ComplianceEngine

config = load_protocol_config("config/medical_protocols.yaml")
result = ComplianceEngine.verify(patient, context, ai_output, protocol_config=config)
```

---

## How to Navigate

**Want to understand the system?**
1. Read [RATIONALE.md](RATIONALE.md) - Why we built this
2. Read [AGENTS.md](AGENTS.md) - How we work
3. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
4. Read [docs/plans/2026-02-22-medical-protocols-design.md](docs/plans/2026-02-22-medical-protocols-design.md) - Medical protocols design

**Want to start building?**
1. Read [docs/standards/OPERATIONAL_WORKFLOWS.md](docs/standards/OPERATIONAL_WORKFLOWS.md)
2. Read [EXTRACTION_LAYER_DESIGN.md](docs/technical/EXTRACTION_LAYER_DESIGN.md)
3. Look at existing code in `src/protocols/`

**Want to understand requirements?**
1. Read [PRODUCT_CASE.md](docs/business/PRODUCT_CASE.md) - Strategic justification
2. Read [VOICE_TRANSCRIPTION_REQUIREMENTS.md](docs/business/VOICE_TRANSCRIPTION_REQUIREMENTS.md) - Functional reqs
3. Read [PRE_MORTEM.md](docs/PRE_MORTEM.md) - What could go wrong

---

## Quick Commands

```bash
# Run tests
uv run pytest tests/ -v

# Check code
uv run ruff check .

# Type check
uv run mypy src/

# Run API
uv run python main.py

# Validate protocol config ✅ NEW
uv run python cli/protocols.py validate-config

# Test drug interaction ✅ NEW
uv run python cli/protocols.py check --medications "warfarin,ibuprofen"

# Test allergy conflict ✅ NEW
uv run python cli/protocols.py check --allergies "penicillin" --medications "amoxicillin"
```

---

## Key Decisions Made

**Architecture:**
- LLM-based extraction (not rule-based)
- Human-in-the-loop required
- Australian healthcare context (My Health Record, PBS, MBS)
- Data sovereignty (Sydney region)
- **Configurable safety rules via YAML (no code changes)** ✅ NEW

**Safety:**
- Never auto-populate medication changes
- Confidence scoring per extraction
- Pre-mortem analysis completed
- Risk mitigation documented
- **Drug interaction checking** ✅ NEW
- **Allergy conflict detection** ✅ NEW
- **Required field validation** ✅ NEW

---

## Questions?

**Technical:** See [docs/DEBUGGING_GUIDE.md](docs/DEBUGGING_GUIDE.md)
**Architecture:** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
**Testing:** See [docs/standards/TESTING_STANDARDS.md](docs/standards/TESTING_STANDARDS.md)
**Medical Protocols:** See [docs/plans/2026-02-22-medical-protocols-design.md](docs/plans/2026-02-22-medical-protocols-design.md)

---

*Last updated: 2026-02-22*
