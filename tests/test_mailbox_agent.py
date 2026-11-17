from __future__ import annotations

import email
import json
from email import policy
from unittest.mock import MagicMock, Mock, patch

import pytest

from mailbox_agent import (
    MailMessage,
    OpenRouterSummarizer,
    load_config,
    read_messages,
    send_test_email,
)


def _raw_message(subject: str, body: str) -> bytes:
    message = email.message.EmailMessage()
    message["Subject"] = subject
    message["From"] = "sender@example.com"
    message["Date"] = "Tue, 17 Nov 2026 10:00:00 +0000"
    message.set_content(body)
    return message.as_bytes(policy=policy.default)


def test_read_messages_selects_read_only_and_fetches_latest_with_peek() -> None:
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.select.return_value = ("OK", [b"10"])
    connection.search.return_value = ("OK", [b"1 2 3"])
    connection.fetch.side_effect = [
        ("OK", [(b"3 (BODY[])", _raw_message("Latest", "latest body"))]),
        ("OK", [(b"2 (BODY[])", _raw_message("Previous", "previous body"))]),
    ]

    with patch("mailbox_agent.imaplib.IMAP4_SSL", return_value=connection):
        messages = read_messages("mail.example.com", 993, "user", "password", 2)

    connection.login.assert_called_once_with("user", "password")
    connection.select.assert_called_once_with("INBOX", readonly=True)
    assert [message.subject for message in messages] == ["Latest", "Previous"]
    assert messages[0].body == "latest body"
    assert [call.args[1] for call in connection.fetch.call_args_list] == [
        "(BODY.PEEK[])",
        "(BODY.PEEK[])",
    ]
    assert not connection.store.called


def test_load_config_requires_all_runtime_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IMAP_USERNAME", raising=False)
    monkeypatch.delenv("IMAP_PASSWORD", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)

    with pytest.raises(ValueError, match="IMAP_USERNAME"):
        load_config()


def test_load_config_uses_confirmed_provider_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMAP_USERNAME", "mailbox-user")
    monkeypatch.setenv("IMAP_PASSWORD", "mailbox-password")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "test/model")

    config = load_config()

    assert config.imap_host == "mail.phaselabs.co.za"
    assert config.imap_port == 993
    assert config.openrouter_model == "test/model"


def test_openrouter_summarizes_messages_with_configured_model() -> None:
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = json.dumps(
        {"choices": [{"message": {"content": "Two messages need attention."}}]}
    ).encode()
    message = MailMessage(
        subject="Quarterly report",
        sender="sender@example.com",
        date="Tue, 17 Nov 2026 10:00:00 +0000",
        body="Please review the attached report.",
    )
    summarizer = OpenRouterSummarizer("test-api-key", "test/model")

    with patch("mailbox_agent.urllib.request.urlopen", return_value=response) as urlopen:
        summary = summarizer.summarize([message])

    request = urlopen.call_args.args[0]
    request_body = json.loads(request.data)
    assert request.full_url == "https://openrouter.ai/api/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer test-api-key"
    assert request_body["model"] == "test/model"
    assert "Quarterly report" in request_body["messages"][1]["content"]
    assert summary == "Two messages need attention."


def test_send_test_email_sends_once_over_ssl() -> None:
    smtp = MagicMock()
    smtp_connection = MagicMock()
    smtp_connection.__enter__.return_value = smtp_connection

    with patch("mailbox_agent.smtplib.SMTP_SSL", return_value=smtp_connection) as smtp_ssl:
        send_test_email("mail.example.com", 465, "user@example.com", "password", "target@example.com")

    smtp_ssl.assert_called_once()
    smtp_connection.login.assert_called_once_with("user@example.com", "password")
    smtp_connection.send_message.assert_called_once()
    sent_message = smtp_connection.send_message.call_args.args[0]
    assert sent_message["To"] == "target@example.com"
    assert sent_message["Subject"] == "Mailbox agent SMTP test"
