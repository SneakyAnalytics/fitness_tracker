import os
import smtplib
from email.message import EmailMessage


def send_email(subject: str, body: str) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    email_to = os.getenv("EMAIL_TO")
    email_from = os.getenv("EMAIL_FROM") or smtp_user

    if not all([smtp_host, smtp_user, smtp_pass, email_to, email_from]):
        raise RuntimeError("Missing SMTP_* or EMAIL_* env vars")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


if __name__ == "__main__":
    subject = os.getenv("EMAIL_SUBJECT", "Zwift Sync Status")
    body = os.getenv("EMAIL_BODY", "Zwift sync completed.")
    send_email(subject, body)
