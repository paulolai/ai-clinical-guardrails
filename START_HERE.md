# Start Here

**New to this project?** This file tells you what's been done and what to do next.

---

## Current Status (Quick)

**Phase:** 1.4 - LLM Client Integration
**Last Updated:** 2026-02-21
**Status:** 🔄 IN PROGRESS

**What's Done:**
- ✅ Verification engine (compliance checking)
- ✅ FHIR integration
- ✅ Business requirements (15+ docs)
- ✅ Risk analysis (pre-mortem complete)
- ✅ Sample transcripts (10 examples)
- ✅ Extraction module scaffold (llm_parser.py, models.py, temporal.py)

**What's Next:**
- ⏳ **Implement LLM client** (OpenAI/Azure integration)
- ⏳ Test extraction accuracy against samples
- ⏳ Build end-to-end workflow

---

## Immediate Next Task

### Task 1.4.1: Implement LLM Client

**Goal:** Create abstraction for calling LLM APIs

**Files:**
- Create: `src/extraction/llm_client.py`
- Update: `src/extraction/llm_parser.py` (wire in client)

**Requirements:**
1. Support OpenAI API
2. Support Azure OpenAI (Australian region)
3. Abstract provider so we can swap implementations
4. Handle JSON response parsing
5. Error handling with retries

**Acceptance Criteria:**
- Can extract structured data from transcript using real LLM API
- Works with sample transcripts in tests/fixtures/

**Example Usage:**
```python
from src.extraction.llm_client import OpenAIClient
from src.extraction.llm_parser import LLMTranscriptParser

client = OpenAIClient(api_key="...")
parser = LLMTranscriptParser(llm_client=client)
result = await parser.parse("Patient came in yesterday...")
```

---

## How to Navigate

**Want to understand the system?**
1. Read [RATIONALE.md](RATIONALE.md) - Why we built this
2. Read [AGENTS.md](AGENTS.md) - How we work
3. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design

**Want to start building?**
1. Read [docs/standards/OPERATIONAL_WORKFLOWS.md](docs/standards/OPERATIONAL_WORKFLOWS.md)
2. Read [EXTRACTION_LAYER_DESIGN.md](docs/technical/EXTRACTION_LAYER_DESIGN.md)
3. Look at existing code in `src/extraction/`

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
```

---

## Key Decisions Made

**Architecture:**
- LLM-based extraction (not rule-based)
- Human-in-the-loop required
- Australian healthcare context (My Health Record, PBS, MBS)
- Data sovereignty (Sydney region)

**Safety:**
- Never auto-populate medication changes
- Confidence scoring per extraction
- Pre-mortem analysis completed
- Risk mitigation documented

---

## Questions?

**Technical:** See [docs/DEBUGGING_GUIDE.md](docs/DEBUGGING_GUIDE.md)
**Architecture:** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
**Testing:** See [docs/standards/TESTING_STANDARDS.md](docs/standards/TESTING_STANDARDS.md)

---

*Last updated: 2026-02-21*
