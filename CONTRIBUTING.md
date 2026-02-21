# Contributing Guide

## Getting Started

1. Read [AGENTS.md](AGENTS.md) - Core principles
2. Complete [Quickstart](docs/QUICKSTART.md) - 15-min tutorial
3. Review [Architecture](docs/ARCHITECTURE.md) - System design

## Development Workflow

### Adding a New Compliance Rule

**Step 1: Define the Rule**

Add to `src/engine.py`:

```python
def _check_rules(self, ai_output: AIOutput, emr: EMRContext) -> list[Violation]:
    violations = []
    # Existing rules...
    
    # Your new rule
    if self._check_medication_interactions(ai_output, emr):
        violations.append(Violation(
            rule_id="MEDICATION_INTERACTION",
            severity="CRITICAL",
            message="Potential medication interaction detected"
        ))
    
    return violations
```

**Step 2: Write Property Test**

```python
# tests/test_compliance.py
@given(medication_contexts(), ai_outputs_with_medications())
def test_medication_interaction_detected(ctx, output):
    result = ComplianceEngine.verify(ctx, output)
    if has_interaction(output.medications, ctx.current_medications):
        assert result.is_failure
```

**Step 3: Add Component Test**

```python
# tests/component/test_engine.py
@pytest.mark.component
async def test_medication_rule_against_real_data():
    # Test against real FHIR patient with medications
    ...
```

**Step 4: PR Checklist**

- [ ] Component test passes
- [ ] Property test passes
- [ ] Documentation updated
- [ ] Learning captured (if applicable)

## Code Style

- Type hints required
- Result[T, E] for external calls
- Never return None for errors
- Docstrings for public APIs

## Testing Requirements

- Component tests before mocks
- Property tests for invariants
- >80% coverage

## PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactoring

## Testing
- [ ] Component tests pass
- [ ] Property tests pass
- [ ] Coverage >80%

## Checklist
- [ ] Code follows AGENTS.md principles
- [ ] Documentation updated
- [ ] Learning captured (if significant)
```
