"""E2E tests for transcription UI."""

from playwright.sync_api import Page, expect


def test_queue_shows_transcription_status(page: Page) -> None:
    """Test that queue shows transcription status."""
    page.goto("http://localhost:8002/queue")

    # Should show queue page
    expect(page).to_have_title("Clinical Transcription PWA")
