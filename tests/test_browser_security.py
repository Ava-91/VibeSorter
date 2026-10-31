from __future__ import annotations

import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from vibesorter.browser.server import _validate_bind_host, create_app


def _serve(db: Path, *, label_session=None, allow_embedding=False):
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_app(db, label_session=label_session, allow_embedding=allow_embedding))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_address[1]}"


def test_browser_sets_security_headers(tmp_path: Path):
    server, thread, base = _serve(tmp_path / "missing.db")
    try:
        with urlopen(base + "/api/status", timeout=3) as response:
            assert response.headers["X-Content-Type-Options"] == "nosniff"
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["Referrer-Policy"] == "no-referrer"
            assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_browser_rejects_foreign_host_header(tmp_path: Path):
    server, thread, base = _serve(tmp_path / "missing.db")
    try:
        request = Request(base + "/api/status", headers={"Host": f"attacker.example:{server.server_address[1]}"})
        with pytest.raises(HTTPError) as error:
            urlopen(request, timeout=3)
        assert error.value.code == 403
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_state_changing_endpoint_requires_same_origin_json(tmp_path: Path):
    server, thread, base = _serve(tmp_path / "missing.db", label_session=object())
    try:
        request = Request(
            base + "/api/label/undo",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as error:
            urlopen(request, timeout=3)
        assert error.value.code == 403
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_non_loopback_binding_requires_explicit_opt_in(capsys):
    with pytest.raises(ValueError, match="--allow-network"):
        _validate_bind_host("0.0.0.0", False)

    _validate_bind_host("0.0.0.0", True)
    assert "WARNING" in capsys.readouterr().err


def test_desktop_embedding_is_limited_to_tauri_origins(tmp_path: Path):
    server, thread, base = _serve(tmp_path / "missing.db", allow_embedding=True)
    try:
        with urlopen(base + "/api/status", timeout=3) as response:
            assert response.headers.get("X-Frame-Options") is None
            assert response.headers["Cross-Origin-Resource-Policy"] == "cross-origin"
            policy = response.headers["Content-Security-Policy"]
            assert "frame-ancestors tauri://localhost http://tauri.localhost" in policy
            assert "frame-ancestors 'none'" not in policy
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
