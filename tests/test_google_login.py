import app as smartapply_app


def test_google_login_redirects_to_dashboard_in_demo_mode(monkeypatch, tmp_path):
    db_path = tmp_path / "smartapply.db"
    monkeypatch.setattr(smartapply_app, "app", smartapply_app.app)
    monkeypatch.setattr(smartapply_app.app, "config", {**smartapply_app.app.config, "DATABASE_PATH": str(db_path)})
    monkeypatch.setattr(smartapply_app, "GOOGLE_DEMO_MODE", True)
    monkeypatch.setattr(smartapply_app, "GOOGLE_ENABLED", True)
    monkeypatch.setattr(smartapply_app, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(smartapply_app, "GOOGLE_CLIENT_SECRET", "")
    monkeypatch.setattr(smartapply_app, "oauth", None)

    smartapply_app.init_db()

    client = smartapply_app.app.test_client()
    response = client.get("/auth/google/login", follow_redirects=True)

    assert response.status_code == 200
    assert response.request.path == "/dashboard"
