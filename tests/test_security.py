from src.notifier import Notification, redact_secrets, send_notification


def test_redact_secrets_in_notification_body():
    body = "token=ghp_abc123 password=super_secret api_key=K3Y-123"

    redacted = redact_secrets(body)

    assert "ghp_abc123" not in redacted
    assert "super_secret" not in redacted
    assert "K3Y-123" not in redacted
    assert "[REDACTED]" in redacted


def test_send_notification_redacts_webhook_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        status = 200

    def fake_urlopen(request, timeout):
        captured["payload"] = request.data.decode("utf-8")
        return FakeResponse()

    monkeypatch.setattr("src.notifier.request.urlopen", fake_urlopen)

    notification = Notification(
        title="Docs Sync",
        body="token=ghp_secret password=topsecret",
    )

    sent = send_notification(notification, webhook_url="https://example.test/webhook")

    assert sent is True
    assert "ghp_secret" not in captured["payload"]
    assert "topsecret" not in captured["payload"]
    assert "[REDACTED]" in captured["payload"]
