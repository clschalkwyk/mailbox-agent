# Mailbox Reader Agent

A small command-line agent that reads the latest messages in an IMAP inbox and summarizes them with OpenRouter. It connects to `mail.phaselabs.co.za` over IMAP SSL on port `993` by default.

Normal runs open `INBOX` in read-only mode and fetch message bodies with `BODY.PEEK[]`; they do not send, delete, archive, mark, or otherwise modify messages. Email content is sent to OpenRouter for summarization. A separate, explicit `--send-test-email` option sends one fixed test message through SSL SMTP and is not used by normal runs.

## Setup

Use Python 3.10 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cp .env.example .env
```

Set the values in `.env`, then export them to the process environment before running:

```bash
set -a
source .env
set +a
python -m mailbox_agent
```

Alternatively, export the variables using your shell or secret manager. Never commit `.env` or real credentials. `OPENROUTER_MODEL` must be a model identifier available to your OpenRouter account.

## Usage

```bash
python -m mailbox_agent
python -m mailbox_agent --limit 5
python -m mailbox_agent --send-test-email recipient@example.com
```

The default is the 10 latest messages in `INBOX`. Message bodies are limited to 3,000 characters each before being sent for summarization. Only plain-text email parts are included; attachments and HTML-only content are omitted. `--send-test-email` sends a message with the subject `Mailbox agent SMTP test`; it uses the mailbox username and password and must be requested explicitly.

## Environment variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `IMAP_HOST` | No | `mail.phaselabs.co.za` | IMAP server hostname |
| `IMAP_PORT` | No | `993` | IMAP over SSL port |
| `IMAP_USERNAME` | Yes | — | Mailbox username |
| `IMAP_PASSWORD` | Yes | — | Mailbox password |
| `SMTP_HOST` | No | `mail.phaselabs.co.za` | SMTP server hostname |
| `SMTP_PORT` | No | `465` | SMTP over SSL port |
| `OPENROUTER_API_KEY` | Yes | — | OpenRouter API key |
| `OPENROUTER_MODEL` | Yes | — | OpenRouter model identifier |

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```
