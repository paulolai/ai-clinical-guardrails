#!/usr/bin/env python3
import datetime
import re
from pathlib import Path
from typing import Any

ADR_FILE = Path("docs/ARCHITECTURE_DECISIONS.md")
OUTPUT_FILE = Path("ADR-extracts.md")


def parse_adrs(content: str) -> list[dict[str, Any]]:
    """
    Parses the ARCHITECTURE_DECISIONS.md file into structured ADR objects.
    Returns a list of dicts: {number, title, category, content, status}
    """
    adrs: list[dict[str, Any]] = []

    # regex for Category headers: ## I. Testing Strategy
    category_pattern = re.compile(r"^##\s+[IVXLCDM]+\.\s+(.+)$", re.MULTILINE)

    # regex for ADR headers: ### 1. Testing Scope...
    adr_pattern = re.compile(r"^###\s+(\d+)\.\s+(.+)$", re.MULTILINE)

    # Split content by lines to process sequentially
    lines = content.split("\n")

    current_category = "General"
    current_adr: dict[str, Any] | None = None

    for line in lines:
        # Check for Category
        cat_match = category_pattern.match(line)
        if cat_match:
            current_category = cat_match.group(1).strip()
            continue

        # Check for ADR
        adr_match = adr_pattern.match(line)
        if adr_match:
            # Save previous ADR if exists
            if current_adr:
                adrs.append(current_adr)

            current_adr = {
                "number": int(adr_match.group(1)),
                "title": adr_match.group(2).strip(),
                "category": current_category,
                "lines": [],
                "status": "Unknown",
            }
            continue

        # Append content to current ADR
        if current_adr:
            current_adr["lines"].append(line)
            # Extract Status
            if line.strip().startswith("**Status:**"):
                status_match = re.search(r"\*\*Status:\*\*\s+(\w+)", line)
                if status_match:
                    current_adr["status"] = status_match.group(1)

    # Append last ADR
    if current_adr:
        adrs.append(current_adr)

    return adrs


def extract_rules(adr: dict[str, Any]) -> list[dict[str, str]]:
    """
    Extracts executable rules from an ADR's content lines.
    Looks for sections like '#### Rule', '#### The Decision', etc.
    """
    rules: list[dict[str, str]] = []
    lines = adr["lines"]
    current_section = ""

    for line in lines:
        if line.startswith("####"):
            current_section = line.replace("####", "").strip()
            continue

        if not line.strip():
            continue

        # We only care about specific sections for the summary
        target_sections = ["Rule", "The Decision", "The Pattern", "Configuration"]

        if any(s in current_section for s in target_sections):
            # Clean up list items
            clean_line = line.strip()
            if clean_line.startswith("*") or clean_line.startswith("-"):
                clean_line = clean_line[1:].strip()

            # Skip code blocks markers
            if clean_line.startswith("```"):
                continue

            # Skip images
            if clean_line.startswith("!["):
                continue

            # Skip empty or very short lines
            if len(clean_line) < 5:
                continue

            type_label = "INFO"
            if "Rule" in current_section:
                type_label = "MUST"
            elif "Decision" in current_section:
                type_label = "DECISION"
            elif "Configuration" in current_section:
                type_label = "CONFIG"

            rules.append({"type": type_label, "section": current_section, "text": clean_line})

    return rules


def generate_markdown(adrs: list[dict[str, Any]]) -> str:
    """Generates the summary markdown."""
    output = []
    output.append("# ADR Extracts for AI Agents")
    output.append("")
    output.append(f"This document is **GENERATED** from `{ADR_FILE}`.")
    output.append("DO NOT EDIT MANUALLY - Changes will be overwritten.")
    output.append("")
    output.append(f"Last generated: {datetime.datetime.now().isoformat()}")
    output.append("")
    output.append("---")
    output.append("")

    # Group by Category
    adrs_by_category: dict[str, list[dict[str, Any]]] = {}
    for adr in adrs:
        if adr["category"] not in adrs_by_category:
            adrs_by_category[adr["category"]] = []
        adrs_by_category[adr["category"]].append(adr)

    for category, category_adrs in adrs_by_category.items():
        output.append(f"## {category}")
        output.append("")

        for adr in category_adrs:
            rules = extract_rules(adr)
            if not rules:
                continue

            for rule in rules:
                icon = "ℹ️"
                if rule["type"] == "MUST":
                    icon = "✅"
                elif rule["type"] == "DECISION":
                    icon = "🏛️"
                elif rule["type"] == "CONFIG":
                    icon = "⚙️"

                output.append(f"{icon} **[{rule['type']}]** {rule['text']}")
                output.append(f"   *ADR-{adr['number']}: {adr['title']}* ({rule['section']})")
                output.append("")

        output.append("---")
        output.append("")

    return "\n".join(output)


def main() -> None:
    if not ADR_FILE.exists():
        print(f"Error: {ADR_FILE} not found.")
        return

    content = ADR_FILE.read_text()
    adrs = parse_adrs(content)
    markdown = generate_markdown(adrs)

    OUTPUT_FILE.write_text(markdown)
    print(f"Generated {OUTPUT_FILE} with {len(adrs)} ADRs.")


if __name__ == "__main__":
    main()
