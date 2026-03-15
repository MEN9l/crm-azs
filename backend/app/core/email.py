"""Отправка email через SMTP (если настроен)."""
import smtplib
from email.mime.text import MIMEText

from app.core.config import settings


def send_email(to: str, subject: str, body_plain: str) -> bool:
    """Отправить письмо. Возвращает True при успехе, False если SMTP не настроен или ошибка."""
    if not (settings.smtp_host and settings.smtp_from and to):
        return False
    try:
        msg = MIMEText(body_plain, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
            if settings.smtp_user and settings.smtp_password:
                s.starttls()
                s.login(settings.smtp_user, settings.smtp_password)
            s.sendmail(settings.smtp_from, [to], msg.as_string())
        return True
    except Exception:
        return False
