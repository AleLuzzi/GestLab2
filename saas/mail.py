"""Invio email SMTP per le comunicazioni operative di GestLab."""

import smtplib
from email.message import EmailMessage

from core.env import get_secret


def smtp_configurato() -> bool:
    """Indica se host e mittente SMTP sono configurati."""
    return bool(get_secret("SMTP_HOST").strip() and get_secret("SMTP_FROM").strip())


def invia_email(destinatario: str, oggetto: str, corpo: str) -> None:
    """Invia un messaggio di testo. Solleva un errore se SMTP non è usabile."""
    host = get_secret("SMTP_HOST").strip()
    mittente = get_secret("SMTP_FROM").strip()
    if not host or not mittente:
        raise RuntimeError("SMTP non configurato")

    port = int(get_secret("SMTP_PORT", "587"))
    utente = get_secret("SMTP_USER").strip()
    password = get_secret("SMTP_PASSWORD")
    use_tls = get_secret("SMTP_USE_TLS", "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }

    messaggio = EmailMessage()
    messaggio["From"] = mittente
    messaggio["To"] = destinatario
    messaggio["Subject"] = oggetto
    messaggio.set_content(corpo)

    with smtplib.SMTP(host, port, timeout=20) as client:
        if use_tls:
            client.starttls()
        if utente:
            client.login(utente, password)
        client.send_message(messaggio)
