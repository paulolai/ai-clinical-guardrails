# Examples

Runnable code examples demonstrating common patterns.

## basic_verification.py

Simple verification of AI output against patient EMR.

```bash
uv run python examples/basic_verification.py
```

## custom_rule.py

Extending the compliance engine with custom rules.

```bash
uv run python examples/custom_rule.py
```

## batch_processing.py

Processing multiple verifications concurrently.

```bash
uv run python examples/batch_processing.py
```

## Running Examples

All examples require:
1. `uv sync` to install dependencies
2. `export PYTHONPATH=$PYTHONPATH:.`
3. Network access to HAPI FHIR sandbox
