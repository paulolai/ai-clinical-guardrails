"""Temporal expression resolution from clinical dictation."""

import re
from datetime import date, timedelta
from re import Pattern

from src.extraction.models import (
    ExtractedTemporalExpression,
    TemporalType,
)


class TemporalResolver:
    """Resolves relative temporal expressions to absolute dates.

    Given an encounter date (the reference point), converts relative
    expressions like "yesterday", "two weeks ago", "in three days"
    to absolute dates.
    """

    # Regex patterns for common temporal expressions
    PATTERNS: dict[str, Pattern[str]] = {
        "today": re.compile(r"\btoday\b", re.IGNORECASE),
        "yesterday": re.compile(r"\byesterday\b", re.IGNORECASE),
        "tomorrow": re.compile(r"\btomorrow\b", re.IGNORECASE),
        "last_night": re.compile(r"\blast night\b", re.IGNORECASE),
        "this_morning": re.compile(r"\bthis morning\b", re.IGNORECASE),
        "days_ago": re.compile(r"\b(\d+|a few|several)\s+days?\s+ago\b", re.IGNORECASE),
        "weeks_ago": re.compile(r"\b(\d+|a few|several)\s+weeks?\s+ago\b", re.IGNORECASE),
        "months_ago": re.compile(r"\b(\d+|a few|several)\s+months?\s+ago\b", re.IGNORECASE),
        "in_days": re.compile(r"\bin\s+(\d+|a few|several)\s+days?\b", re.IGNORECASE),
        "in_weeks": re.compile(r"\bin\s+(\d+|a few|several)\s+weeks?\b", re.IGNORECASE),
        "in_months": re.compile(r"\bin\s+(\d+|a few|several)\s+months?\b", re.IGNORECASE),
        "last_week": re.compile(r"\blast\s+week\b", re.IGNORECASE),
        "next_week": re.compile(r"\bnext\s+week\b", re.IGNORECASE),
        "last_month": re.compile(r"\blast\s+month\b", re.IGNORECASE),
        "next_month": re.compile(r"\bnext\s+month\b", re.IGNORECASE),
        # Ambiguous patterns
        "recently": re.compile(r"\brecently\b", re.IGNORECASE),
        "soon": re.compile(r"\bsoon\b", re.IGNORECASE),
    }

    def __init__(self, reference_date: date | None = None):
        """Initialize resolver with reference date.

        Args:
            reference_date: The base date for relative calculations.
                          Defaults to today if not provided.
        """
        self.reference_date = reference_date or date.today()

    def resolve(self, text: str) -> list[ExtractedTemporalExpression]:
        """Extract and resolve all temporal expressions in text.

        Args:
            text: The clinical dictation text

        Returns:
            List of extracted temporal expressions with resolved dates
        """
        results = []

        for pattern_name, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                extracted = self._resolve_expression(
                    pattern_name, match.group(), match.group(1) if match.groups() else None
                )
                results.append(extracted)

        return results

    def _resolve_expression(self, pattern_name: str, text: str, quantity: str | None) -> ExtractedTemporalExpression:
        """Resolve a single temporal expression."""
        resolvers = {
            "today": self._resolve_today,
            "yesterday": self._resolve_yesterday,
            "tomorrow": self._resolve_tomorrow,
            "last_night": self._resolve_last_night,
            "this_morning": self._resolve_today,
            "days_ago": self._resolve_days_ago,
            "weeks_ago": self._resolve_weeks_ago,
            "months_ago": self._resolve_months_ago,
            "in_days": self._resolve_in_days,
            "in_weeks": self._resolve_in_weeks,
            "in_months": self._resolve_in_months,
            "last_week": self._resolve_last_week,
            "next_week": self._resolve_next_week,
            "last_month": self._resolve_last_month,
            "next_month": self._resolve_next_month,
            "recently": self._resolve_ambiguous,
            "soon": self._resolve_ambiguous,
        }

        resolver = resolvers.get(pattern_name, self._resolve_ambiguous)
        return resolver(text, quantity)

    def _resolve_today(self, text: str, _: str | None) -> ExtractedTemporalExpression:
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date,
            confidence=1.0,
        )

    def _resolve_yesterday(self, text: str, _: str | None) -> ExtractedTemporalExpression:
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date - timedelta(days=1),
            confidence=1.0,
        )

    def _resolve_tomorrow(self, text: str, _: str | None) -> ExtractedTemporalExpression:
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date + timedelta(days=1),
            confidence=1.0,
        )

    def _resolve_last_night(self, text: str, _: str | None) -> ExtractedTemporalExpression:
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date - timedelta(days=1),
            confidence=1.0,
        )

    def _resolve_days_ago(self, text: str, quantity: str | None) -> ExtractedTemporalExpression:
        days = self._parse_quantity(quantity, default=3)
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date - timedelta(days=days),
            confidence=0.7 if quantity in ["a few", "several"] else 0.9,
        )

    def _resolve_weeks_ago(self, text: str, quantity: str | None) -> ExtractedTemporalExpression:
        weeks = self._parse_quantity(quantity, default=2)
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date - timedelta(weeks=weeks),
            confidence=0.7 if quantity in ["a few", "several"] else 0.9,
        )

    def _resolve_months_ago(self, text: str, quantity: str | None) -> ExtractedTemporalExpression:
        months = self._parse_quantity(quantity, default=2)
        # Approximate months as 30 days
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date - timedelta(days=months * 30),
            confidence=0.7 if quantity in ["a few", "several"] else 0.9,
        )

    def _resolve_in_days(self, text: str, quantity: str | None) -> ExtractedTemporalExpression:
        days = self._parse_quantity(quantity, default=3)
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date + timedelta(days=days),
            confidence=0.7 if quantity in ["a few", "several"] else 0.9,
        )

    def _resolve_in_weeks(self, text: str, quantity: str | None) -> ExtractedTemporalExpression:
        weeks = self._parse_quantity(quantity, default=2)
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date + timedelta(weeks=weeks),
            confidence=0.7 if quantity in ["a few", "several"] else 0.9,
        )

    def _resolve_in_months(self, text: str, quantity: str | None) -> ExtractedTemporalExpression:
        months = self._parse_quantity(quantity, default=2)
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date + timedelta(days=months * 30),
            confidence=0.7 if quantity in ["a few", "several"] else 0.9,
        )

    def _resolve_last_week(self, text: str, _: str | None) -> ExtractedTemporalExpression:
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date - timedelta(days=7),
            confidence=0.8,
        )

    def _resolve_next_week(self, text: str, _: str | None) -> ExtractedTemporalExpression:
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date + timedelta(days=7),
            confidence=0.8,
        )

    def _resolve_last_month(self, text: str, _: str | None) -> ExtractedTemporalExpression:
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date - timedelta(days=30),
            confidence=0.8,
        )

    def _resolve_next_month(self, text: str, _: str | None) -> ExtractedTemporalExpression:
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.RELATIVE_DATE,
            normalized_date=self.reference_date + timedelta(days=30),
            confidence=0.8,
        )

    def _resolve_ambiguous(self, text: str, _: str | None) -> ExtractedTemporalExpression:
        return ExtractedTemporalExpression(
            text=text,
            type=TemporalType.AMBIGUOUS,
            normalized_date=None,
            confidence=0.3,
            note="ambiguous temporal reference",
        )

    def _parse_quantity(self, quantity: str | None, default: int) -> int:
        """Parse quantity string to integer."""
        if quantity is None:
            return default

        quantity_map = {
            "a": 1,
            "a few": 3,
            "few": 3,
            "several": 4,
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
        }

        if quantity.lower() in quantity_map:
            return quantity_map[quantity.lower()]

        try:
            return int(quantity)
        except ValueError:
            return default
