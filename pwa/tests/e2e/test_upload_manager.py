"""Playwright tests for Upload Manager."""

from playwright.sync_api import Page


def test_upload_manager_defined(page: Page) -> None:
    """Test that UploadManager is available globally."""
    page.goto("http://localhost:8002/record/patient-123")

    result = page.evaluate("""
        () => {
            return {
                defined: typeof window.UploadManager !== 'undefined',
                hasQueueUpload: typeof window.UploadManager?.queueUpload === 'function',
                hasProcessQueue: typeof window.UploadManager?.processQueue === 'function'
            };
        }
    """)

    assert result["defined"] is True, "UploadManager not defined"
    assert result["hasQueueUpload"] is True, "queueUpload method not found"
    assert result["hasProcessQueue"] is True, "processQueue method not found"


def test_upload_manager_detects_online_status(page: Page) -> None:
    """Test online/offline detection."""
    page.goto("http://localhost:8002/record/patient-123")

    result = page.evaluate("""
        () => {
            if (!window.UploadManager) {
                return { error: 'UploadManager not defined' };
            }
            return {
                isOnline: window.UploadManager.isOnline()
            };
        }
    """)

    assert result.get("error") is None
    assert isinstance(result["isOnline"], bool)
