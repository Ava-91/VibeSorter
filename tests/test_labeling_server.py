import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from vibesorter.browser.server import create_app
from vibesorter.labeling import LabelCandidate, LabelSession
from vibesorter.vibes import VibeScore


def test_label_decision_endpoint_persists_human_label(tmp_path):
    image = tmp_path / "image.jpg"
    image.write_bytes(b"not-used-by-endpoint")
    candidate = LabelCandidate(
        image.resolve(),
        "Retro Blue",
        0.43,
        True,
        (VibeScore("Retro Blue", 0.48), VibeScore("Soft / Pastel", 0.40)),
    )
    output = tmp_path / "labels.jsonl"
    session = LabelSession((candidate,), output)
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_app(tmp_path / "missing.db", label_session=session))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", server.server_port)
        connection.request("POST", "/api/label/decision", body=json.dumps({"path": str(image), "label": "Dark / Moody"}), headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        body = json.loads(response.read())
        assert response.status == 200
        assert body["remaining"] == 0
        assert '"label": "Dark / Moody"' in output.read_text(encoding="utf-8")

        connection.request("GET", "/label")
        response = connection.getresponse()
        page = response.read().decode()
        assert response.status == 200
        assert "Review complete" in page
        connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_label_decision_rejects_unknown_vibe(tmp_path):
    image = tmp_path / "image.jpg"
    candidate = LabelCandidate(image.resolve(), "Retro Blue", 0.43, True, (VibeScore("Retro Blue", 0.48),))
    session = LabelSession((candidate,), tmp_path / "labels.jsonl")
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_app(tmp_path / "missing.db", label_session=session))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", server.server_port)
        connection.request("POST", "/api/label/decision", body=json.dumps({"path": str(image), "label": "Nope"}), headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        body = json.loads(response.read())
        assert response.status == 400
        assert "unknown vibe" in body["error"]
        connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
