"""Test fixtures for Lumen."""

import pytest


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMEN_SECRET_KEY", "test-secret")

    from lumen import store

    store.configure_data_dir(tmp_path / "data")
    store.add_teacher("teacher", "secret")

    from lumen.app import create_app

    application = create_app()
    application.config.update(TESTING=True)
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def teacher(client):
    response = client.post(
        "/login",
        data={"username": "teacher", "password": "secret"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    return client
