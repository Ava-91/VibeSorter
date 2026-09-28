import pytest

from vibesorter.browser.launcher import _is_loopback


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
def test_browser_launcher_accepts_loopback_hosts(host: str):
    assert _is_loopback(host)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20", "example.local"])
def test_browser_launcher_rejects_non_loopback_hosts(host: str):
    assert not _is_loopback(host)
