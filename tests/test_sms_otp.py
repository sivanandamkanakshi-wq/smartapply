import os
import sqlite3

import app as smartapply_app


def test_send_sms_otp_returns_false_when_no_provider_is_configured(monkeypatch):
    monkeypatch.delenv("OTP_DEMO_MODE", raising=False)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_PHONE_NUMBER", raising=False)
    monkeypatch.delenv("TEXTBELT_API_KEY", raising=False)

    assert smartapply_app.send_sms_otp("+919999999999", "123456") is False


def test_login_sends_otp_when_mobile_is_registered(monkeypatch, tmp_path):
    db_path = tmp_path / "smartapply.db"
    monkeypatch.setattr(smartapply_app, "app", smartapply_app.app)
    monkeypatch.setattr(smartapply_app.app, "config", {**smartapply_app.app.config, "DATABASE_PATH": str(db_path)})

    smartapply_app.init_db()

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO users (full_name, email, password, mobile_number) VALUES (?, ?, ?, ?)",
        ("Test User", "user@example.com", smartapply_app.generate_password_hash("pass123"), "+919999999999"),
    )
    conn.commit()
    conn.close()

    sent = {}

    def fake_send_sms_otp(mobile_number, otp_code):
        sent["mobile_number"] = mobile_number
        sent["otp_code"] = otp_code
        return True

    monkeypatch.setattr(smartapply_app, "send_sms_otp", fake_send_sms_otp)

    client = smartapply_app.app.test_client()
    response = client.post(
        "/login",
        data={"email": "user@example.com", "password": "pass123"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert sent["mobile_number"] == "+919999999999"
    assert len(sent["otp_code"]) == 6


def test_send_sms_otp_accepts_normalized_indian_mobile_number(monkeypatch):
    monkeypatch.delenv("OTP_DEMO_MODE", raising=False)
    monkeypatch.setenv("SMS_PROVIDER", "email")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_FROM", "user@example.com")
    monkeypatch.delenv("OTP_RECIPIENT_NUMBER", raising=False)
    monkeypatch.setenv("OTP_RECIPIENT_NUMBER_OVERRIDE", "false")

    monkeypatch.setattr(smartapply_app, "send_email_otp", lambda *args, **kwargs: True)

    assert smartapply_app.send_sms_otp("+919999999999", "123456") is True


def test_login_falls_back_to_email_when_sms_fails(monkeypatch, tmp_path):
    db_path = tmp_path / "smartapply.db"
    monkeypatch.setattr(smartapply_app, "app", smartapply_app.app)
    monkeypatch.setattr(smartapply_app.app, "config", {**smartapply_app.app.config, "DATABASE_PATH": str(db_path)})

    smartapply_app.init_db()

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO users (full_name, email, password, mobile_number) VALUES (?, ?, ?, ?)",
        ("Test User", "user@example.com", smartapply_app.generate_password_hash("pass123"), "+919999999999"),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(smartapply_app, "send_sms_otp", lambda *args, **kwargs: False)
    monkeypatch.setattr(smartapply_app, "send_email_otp", lambda *args, **kwargs: True)

    client = smartapply_app.app.test_client()
    response = client.post(
        "/login",
        data={"email": "user@example.com", "password": "pass123"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"SMS delivery failed" in response.data


def test_demo_mode_allows_otp_delivery_without_provider_credentials(monkeypatch):
    monkeypatch.setenv("OTP_DEMO_MODE", "true")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_PHONE_NUMBER", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)
    monkeypatch.delenv("SMTP_USERNAME", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)

    assert smartapply_app.send_sms_otp("+919999999999", "123456") is True
    assert smartapply_app.send_email_otp("user@example.com", "123456") is True
