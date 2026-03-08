#!/usr/bin/env python3
"""Validate cassette/snapshot changes using LLM analysis.

This script analyzes changes in VCR cassettes and snapshots after re-recording
to determine if they represent significant changes requiring manual review or
are just expected variations (timestamps, tokens, minor wording differences).
"""

import json
import os
import re
import subprocess
import sys
from typing import Any


def get_git_diff(path: str) -> str:
    """Get git diff for a specific path."""
    result = subprocess.run(
        ["git", "diff", "--no-color", path],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def get_changed_files(path: str) -> list[str]:
    """Get list of changed files in a path."""
    result = subprocess.run(
        ["git", "diff", "--name-only", path],
        capture_output=True,
        text=True,
        check=True,
    )
    return [f.strip() for f in result.stdout.split("\n") if f.strip()]


def categorize_change(diff_line: str) -> str:
    """Categorize a single diff line."""
    # These patterns indicate non-significant changes
    benign_patterns = [
        r'"created":\s*\d+',  # Timestamp
        r'"id":\s*"[^"]*"',  # Request ID
        r'"token_ids":',  # Token IDs
        r'"prompt_token_ids":',  # Prompt token IDs
        r'"system_fingerprint":',  # System fingerprint
        r'"service_tier":',  # Service tier
        r'"usage":\s*\{[^}]*"prompt_tokens":',  # Token counts
        r'"x-synthetic-quotas":',  # Quota headers
        r"Date:",  # HTTP Date header
        r"Set-Cookie:",  # Session cookies
        r'"model":\s*"[^"]*"',  # Model name in response
        r'"x-[^:]+:',  # Various x- headers
    ]

    for pattern in benign_patterns:
        if re.search(pattern, diff_line):
            return "benign"

    return "unknown"


def analyze_cassette_diff(diff_text: str) -> dict[str, Any]:
    """Analyze cassette diff to extract meaningful changes."""
    lines = diff_text.split("\n")

    changes: dict[str, Any] = {
        "total_lines": len(lines),
        "added": [],
        "removed": [],
        "benign": [],
        "suspicious": [],
        "response_body_changes": [],
    }

    in_response_body = False

    for line in lines:
        if line.startswith("+") and not line.startswith("+++ "):
            content = line[1:].strip()
            if content:
                changes["added"].append(content)

                # Check if in response body
                if "response:" in content or "body:" in content:
                    in_response_body = True

                if in_response_body and "string:" in content:
                    # This is a response body change
                    changes["response_body_changes"].append(content)

                # Check if suspicious
                cat = categorize_change(content)
                if cat == "benign":
                    changes["benign"].append(content)
                else:
                    changes["suspicious"].append(content)

        elif line.startswith("-") and not line.startswith("--- "):
            content = line[1:].strip()
            if content:
                changes["removed"].append(content)

    return changes


def summarize_changes(changes: list[dict[str, Any]]) -> str:
    """Create a human-readable summary of changes."""
    summary_parts = []

    for change in changes:
        file = change["file"]
        stats = change["analysis"]

        summary_parts.append(f"\n📄 {file}")
        summary_parts.append(f"   Lines changed: {stats['total_lines']}")
        summary_parts.append(f"   Suspicious changes: {len(stats['suspicious'])}")
        summary_parts.append(f"   Benign changes: {len(stats['benign'])}")

        if stats["response_body_changes"]:
            summary_parts.append("   Response body modified: ✓")

    return "\n".join(summary_parts)


def validate_changes_with_llm(changes: list[dict[str, Any]], api_key: str | None = None) -> dict[str, Any]:
    """Use LLM to validate if changes require manual attention."""
    if not api_key:
        # No API key, use heuristic analysis
        return analyze_changes_heuristic(changes)

    # Import here to avoid dependency issues if LLM client not available
    try:
        from src.extraction.llm_client import SyntheticLLMClient
    except ImportError:
        return analyze_changes_heuristic(changes)

    summary = summarize_changes(changes)

    prompt = (
        "You are a test validation expert. Analyze these VCR cassette changes "
        "to determine if they require manual attention.\n\n"
        "VCR cassettes record HTTP responses for integration tests. Changes can be:\n"
        "1. Benign: Timestamps, token counts, session IDs, minor wording variations\n"
        "2. Suspicious: Missing data, changed field names, errors, structural changes\n"
        "3. Breaking: Response format changes, missing fields, error responses\n\n"
        f"Cassette Changes Summary:\n{summary}\n\n"
        "Suspicious changes found:\n"
    )
    # Add suspicious changes to prompt
    for change in changes:
        if change["analysis"]["suspicious"]:
            prompt += f"\nIn {change['file']}:"
            for item in change["analysis"]["suspicious"][:10]:  # Limit to 10
                prompt += f"\n  - {item}"

    prompt += """

Analyze these changes and respond with ONLY a JSON object:
{
  "requires_attention": true/false,
  "severity": "low|medium|high|critical",
  "reason": "Clear explanation of why attention is or isn't needed",
  "action_required": "What action to take (e.g., 'Review manually', 'Accept changes', 'Investigate API')",
  "confidence": 0.0-1.0
}

Consider:
- Are only timestamps/token IDs changing? (benign)
- Are response structures preserved? (benign)
- Are field names or data types changing? (suspicious)
- Are errors appearing? (requires attention)
"""

    try:
        import asyncio
        from typing import cast

        async def call_llm() -> dict[str, Any]:
            client = SyntheticLLMClient(api_key=api_key)
            try:
                response = await client.complete(prompt=prompt, temperature=0.1)
                return cast("dict[str, Any]", json.loads(response.strip()))
            finally:
                await client.close()

        result = asyncio.run(call_llm())
        return {
            "llm_analysis": result,
            "method": "llm",
            "changes": changes,
        }
    except Exception as e:
        # Fall back to heuristic
        result = analyze_changes_heuristic(changes)
        result["llm_error"] = str(e)
        return result


def analyze_changes_heuristic(changes: list[dict[str, Any]]) -> dict[str, Any]:
    """Use heuristics to determine if changes require attention."""
    total_suspicious = sum(len(c["analysis"]["suspicious"]) for c in changes)
    total_benign = sum(len(c["analysis"]["benign"]) for c in changes)
    has_response_changes = any(c["analysis"]["response_body_changes"] for c in changes)

    # Heuristic rules
    if total_suspicious == 0:
        return {
            "requires_attention": False,
            "severity": "low",
            "reason": f"Only benign changes detected ({total_benign} benign modifications)",
            "action_required": "Accept changes",
            "confidence": 0.9,
            "method": "heuristic",
            "changes": changes,
        }

    # Check if suspicious items are just metadata
    metadata_only = all(
        any(pattern in str(item) for pattern in ["created", "id", "token", "fingerprint", "Date:", "Set-Cookie:"])
        for c in changes
        for item in c["analysis"]["suspicious"]
    )

    if metadata_only:
        return {
            "requires_attention": False,
            "severity": "low",
            "reason": "Changes are primarily metadata (timestamps, IDs, tokens)",
            "action_required": "Accept changes",
            "confidence": 0.8,
            "method": "heuristic",
            "changes": changes,
        }

    if has_response_changes and total_suspicious > 5:
        return {
            "requires_attention": True,
            "severity": "medium",
            "reason": f"Response body modified with {total_suspicious} suspicious changes",
            "action_required": "Review manually",
            "confidence": 0.7,
            "method": "heuristic",
            "changes": changes,
        }

    return {
        "requires_attention": total_suspicious > 10,
        "severity": "medium" if total_suspicious > 10 else "low",
        "reason": f"{total_suspicious} potentially significant changes detected",
        "action_required": "Review manually" if total_suspicious > 10 else "Accept changes",
        "confidence": 0.6,
        "method": "heuristic",
        "changes": changes,
    }


def main() -> None:
    """Main entry point."""
    cassettes_path = "tests/component/cassettes/"
    snapshots_path = "tests/component/__snapshots__/"

    all_changes = []

    # Analyze cassette changes
    if os.path.exists(cassettes_path):
        changed_cassettes = get_changed_files(cassettes_path)
        for cassette_file in changed_cassettes:
            if cassette_file.endswith(".yaml"):
                diff = get_git_diff(cassette_file)
                analysis = analyze_cassette_diff(diff)
                all_changes.append(
                    {
                        "file": cassette_file,
                        "type": "cassette",
                        "analysis": analysis,
                    }
                )

    # Analyze snapshot changes
    if os.path.exists(snapshots_path):
        changed_snapshots = get_changed_files(snapshots_path)
        for snapshot_file in changed_snapshots:
            diff = get_git_diff(snapshot_file)
            analysis = analyze_cassette_diff(diff)  # Similar analysis
            all_changes.append(
                {
                    "file": snapshot_file,
                    "type": "snapshot",
                    "analysis": analysis,
                }
            )

    if not all_changes:
        print("✅ No cassette or snapshot changes detected")
        sys.exit(0)

    print(f"📝 Analyzing {len(all_changes)} changed files...")
    print(summarize_changes(all_changes))

    # Get API key if available
    api_key = os.environ.get("SYNTHETIC_API_KEY")

    # Validate changes
    result = validate_changes_with_llm(all_changes, api_key)

    # Output results
    print("\n" + "=" * 60)
    print("📊 Validation Results")
    print("=" * 60)
    print(f"Method: {result['method']}")
    print(f"Requires Attention: {'⚠️ YES' if result['requires_attention'] else '✅ No'}")
    print(f"Severity: {result['severity']}")
    print(f"Confidence: {result['confidence']:.0%}")
    print(f"\n📝 Reason: {result['reason']}")
    print(f"\n📋 Action Required: {result['action_required']}")

    if "llm_analysis" in result:
        print("\n🤖 LLM Analysis:")
        llm = result["llm_analysis"]
        print(f"   Requires Attention: {llm.get('requires_attention')}")
        print(f"   Severity: {llm.get('severity')}")
        print(f"   Reason: {llm.get('reason')}")

    if "llm_error" in result:
        print(f"\n⚠️ LLM Error (fell back to heuristic): {result['llm_error']}")

    print("\n" + "=" * 60)

    # Exit with appropriate code
    if result["requires_attention"]:
        print("❌ FAIL: Changes require manual review")
        sys.exit(1)
    else:
        print("✅ PASS: Changes are acceptable")
        sys.exit(0)


if __name__ == "__main__":
    main()
