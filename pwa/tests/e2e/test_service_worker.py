"""Playwright tests for Service Worker."""

from playwright.sync_api import Page


def test_service_worker_registers(page: Page) -> None:
    """Test that service worker registers successfully."""
    page.goto("http://localhost:8002/")

    # Wait for registration to complete
    page.wait_for_timeout(2000)

    result = page.evaluate("""
        async () => {
            if (!('serviceWorker' in navigator)) {
                return { error: 'Service Worker not supported' };
            }

            // Get all registrations to find ours
            const registrations = await navigator.serviceWorker.getRegistrations();
            if (registrations.length === 0) {
                return { error: 'No service worker registration found' };
            }

            // Find registration for /static/js/ scope
            const swReg = registrations.find(r => r.scope.includes('/static/js/'));
            if (!swReg) {
                return {
                    error: 'Service Worker registration not found for /static/js/',
                    scopes: registrations.map(r => r.scope)
                };
            }

            return {
                registered: true,
                scope: swReg.scope,
                state: swReg.active?.state || swReg.installing?.state || swReg.waiting?.state
            };
        }
    """)

    assert result.get("error") is None, f"Service Worker error: {result.get('error')}"
    assert result["registered"] is True, "Service Worker not registered"


def test_service_worker_caches_assets(page: Page) -> None:
    """Test that static assets are cached."""
    page.goto("http://localhost:8002/")

    # Wait for SW to be ready
    page.wait_for_timeout(1000)

    result = page.evaluate("""
        async () => {
            const cacheNames = await caches.keys();
            return {
                hasCache: cacheNames.length > 0,
                cacheNames: cacheNames
            };
        }
    """)

    assert result["hasCache"] is True, "No caches found"
