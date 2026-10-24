"""Trimiterea e-mailului: raportul în corpul mesajului și, în plus, ca fișier atașat."""

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def send_report(subject: str, html: str, attachment: Path) -> None:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    recipients = [a.strip() for a in os.environ["MAIL_TO"].split(",") if a.strip()]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("MAIL_FROM", user)
    msg["To"] = ", ".join(recipients)
    msg.set_content("Raportul zilnic este în format HTML; deschide fișierul atașat.")
    msg.add_alternative(html, subtype="html")
    msg.add_attachment(
        attachment.read_bytes(), maintype="text", subtype="html", filename=attachment.name
    )

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=60) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=60) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)
