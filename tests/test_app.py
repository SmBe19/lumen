"""Tests for the Flask views."""

import io
import zipfile

from lumen import store


def _create_exam(client, **overrides):
    data = {
        "name": "Math",
        "exam_key": "ABC123",
        "interval": "5",
        "scale": "0.5",
    }
    data.update(overrides)
    response = client.post("/teacher/exams", data=data, follow_redirects=False)
    assert response.status_code == 302
    exam = store.list_exams(force=True)[0]
    return exam


def test_favicon_is_served(client):
    page = client.get("/")
    assert b'rel="icon"' in page.data
    icon = client.get("/static/favicon.svg")
    assert icon.status_code == 200
    assert icon.mimetype == "image/svg+xml"
    assert b"<svg" in icon.data


def test_login_required_redirects(client):
    response = client.get("/teacher/exams")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_rejects_bad_password(client):
    response = client.post(
        "/login", data={"username": "teacher", "password": "nope"}, follow_redirects=True
    )
    assert b"Invalid username or password" in response.data


def test_student_pages_are_translated(client, teacher):
    exam = _create_exam(teacher)
    teacher.post(
        f"/teacher/exams/{exam['id']}/students/import",
        data={"csv": "firstname\nJane\n"},
        follow_redirects=True,
    )
    german = client.get("/", headers={"Accept-Language": "de-DE,de;q=0.9"})
    assert "Einer Prüfung beitreten".encode() in german.data
    french = client.get(
        f"/exam/ABC123", headers={"Accept-Language": "fr-FR,fr;q=0.9"}
    )
    assert french.status_code == 200
    assert "Choisissez votre nom".encode() in french.data
    assert b"step hidden" in french.data


def test_semicolon_csv_with_extra_columns(teacher):
    exam = _create_exam(teacher)
    csv = (
        "Name;Vorname;Klasse;Adresse;PLZ;Ort;EMail;Telefon\n"
        'User;Test;1A;"Beispielstrasse 42";4200;Bern;test.user@example.com;\n'
    )
    response = teacher.post(
        f"/teacher/exams/{exam['id']}/students/import",
        data={"csv": csv},
        follow_redirects=True,
    )
    assert response.status_code == 200
    config = store.get_exam(exam["id"], force=True)
    assert [s["name"] for s in config["students"]] == ["Test User (1A)"]


def test_create_import_and_config_pages(teacher):
    exam = _create_exam(teacher)
    csv = "firstname,lastname,displayname,class\nJane,Doe,,1a\nJohn,Smith,js,1b\n"
    teacher.post(
        f"/teacher/exams/{exam['id']}/students/import",
        data={"csv": csv},
        follow_redirects=True,
    )
    config = store.get_exam(exam["id"], force=True)
    assert [s["name"] for s in config["students"]] == ["Jane Doe (1a)", "js (1b)"]

    page = teacher.get(f"/teacher/exams/{exam['id']}")
    assert page.status_code == 200
    assert b"Jane Doe (1a)" in page.data

    monitor = teacher.get(f"/teacher/exams/{exam['id']}/monitor")
    assert monitor.status_code == 200


def test_exam_key_must_be_unique(teacher):
    _create_exam(teacher, exam_key="KEY001")
    response = teacher.post(
        "/teacher/exams",
        data={"name": "Other", "exam_key": "KEY001", "interval": "5", "scale": "0.5"},
        follow_redirects=True,
    )
    assert b"already in use" in response.data
    assert len(store.list_exams(force=True)) == 1


def test_config_update_forces_disk_read(teacher):
    exam = _create_exam(teacher, interval="5", scale="0.5")
    teacher.post(
        f"/teacher/exams/{exam['id']}",
        data={"name": "Math 2", "exam_key": "ABC123", "interval": "7", "scale": "0.25"},
        follow_redirects=True,
    )
    config = store.get_exam(exam["id"], force=True)
    assert config["name"] == "Math 2"
    assert config["interval"] == 7
    assert config["scale"] == 0.25


def test_screenshots_discarded_when_not_recording(teacher):
    exam = _create_exam(teacher)
    teacher.post(
        f"/teacher/exams/{exam['id']}/students/import",
        data={"csv": "firstname\nJane\n"},
        follow_redirects=True,
    )
    data = {"name": "Jane", "screenshot": (io.BytesIO(b"pngdata"), "s.png")}
    response = teacher.post(
        "/api/exam/ABC123/screenshot", data=data, content_type="multipart/form-data"
    )
    assert response.get_json()["status"] == "discarded"
    assert store.list_screenshots(exam["id"], "Jane") == []


def test_screenshots_stored_while_recording(app, teacher):
    exam = _create_exam(teacher)
    teacher.post(
        f"/teacher/exams/{exam['id']}/students/import",
        data={"csv": "firstname\nJane\n"},
        follow_redirects=True,
    )
    teacher.post(f"/teacher/exams/{exam['id']}/recording", data={"action": "start"})

    data = {"name": "Jane", "screenshot": (io.BytesIO(b"pngdata"), "s.png")}
    response = teacher.post(
        "/api/exam/ABC123/screenshot", data=data, content_type="multipart/form-data"
    )
    assert response.get_json()["status"] == "ok"
    assert len(store.list_screenshots(exam["id"], "Jane")) == 1


def test_student_config_endpoint_is_public(client, teacher):
    exam = _create_exam(teacher)
    teacher.post(
        f"/teacher/exams/{exam['id']}/students/import",
        data={"csv": "firstname\nJane\n"},
        follow_redirects=True,
    )
    response = client.get("/api/exam/ABC123/config")
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["interval"] == 5
    assert payload["students"] == ["Jane"]


def test_monitor_data_marks_inactive_and_duplicates(teacher):
    import time

    exam = _create_exam(teacher, interval="10", scale="0.5")
    teacher.post(
        f"/teacher/exams/{exam['id']}/students/import",
        data={"csv": "firstname\nJane\nBob\n"},
        follow_redirects=True,
    )
    config = store.get_exam(exam["id"], force=True)
    jane = store.student_by_name(config, "Jane")
    bob = store.student_by_name(config, "Bob")

    now = time.time()
    # Jane: many recent shots -> duplicate warning.
    for i in range(8):
        store.save_screenshot(exam["id"], jane["dir"], b"x", received_ts=now - i)
    # Bob: one old shot -> inactive.
    store.save_screenshot(exam["id"], bob["dir"], b"x", received_ts=now - 3600)

    payload = teacher.get(f"/teacher/exams/{exam['id']}/data").get_json()
    by_name = {s["name"]: s for s in payload["students"]}
    assert by_name["Jane"]["duplicate_warning"] is True
    assert by_name["Bob"]["inactive"] is True
    assert [s["name"] for s in payload["inactive_students"]] == ["Bob"]


def test_manual_log_entry(teacher):
    exam = _create_exam(teacher)
    teacher.post(
        f"/teacher/exams/{exam['id']}/students/import",
        data={"csv": "firstname\nJane\n"},
        follow_redirects=True,
    )
    teacher.post(
        f"/teacher/exams/{exam['id']}/student/Jane/log",
        data={"message": "left the room"},
        follow_redirects=True,
    )
    logs = store.read_logs(exam["id"], "Jane")
    assert any(entry["message"] == "left the room" for entry in logs)


def test_default_interval_is_ten(teacher):
    exam = _create_exam(teacher, interval="")
    assert exam["interval"] == 10


def test_import_without_valid_columns_reports_error(teacher):
    exam = _create_exam(teacher)
    response = teacher.post(
        f"/teacher/exams/{exam['id']}/students/import",
        data={"csv": "Jane,Doe\nJohn,Smith\n"},
        follow_redirects=True,
    )
    assert b"No valid columns" in response.data
    assert store.get_exam(exam["id"], force=True)["students"] == []


def test_delete_single_student(teacher):
    exam = _create_exam(teacher)
    teacher.post(
        f"/teacher/exams/{exam['id']}/students/import",
        data={"csv": "firstname\nJane\nBob\n"},
        follow_redirects=True,
    )
    store.save_screenshot(exam["id"], "Jane", b"pngdata")
    response = teacher.post(
        f"/teacher/exams/{exam['id']}/student/Jane/delete",
        follow_redirects=True,
    )
    assert response.status_code == 200
    config = store.get_exam(exam["id"], force=True)
    assert [s["name"] for s in config["students"]] == ["Bob"]
    assert not store.screenshot_dir(exam["id"], "Jane").exists()


def test_exam_key_lookup_cache_refreshes(teacher):
    first = _create_exam(teacher, exam_key="AAA111")
    assert store.get_exam_by_key("AAA111")["id"] == first["id"]
    _create_exam(teacher, name="Second", exam_key="BBB222")
    second = next(
        exam for exam in store.list_exams(force=True)
        if exam["exam_key"] == "BBB222"
    )
    assert store.get_exam_by_key("BBB222")["id"] == second["id"]


def test_zip_includes_logs(teacher):
    exam = _create_exam(teacher)
    teacher.post(
        f"/teacher/exams/{exam['id']}/students/import",
        data={"csv": "firstname\nJane\n"},
        follow_redirects=True,
    )
    store.append_log(exam["id"], "Jane", "note", "looked away")
    response = teacher.get(f"/teacher/exams/{exam['id']}/student/Jane/download")
    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        assert "Jane/log.jsonl" in archive.namelist()


def test_monitor_issues_include_manual_notes(teacher):
    exam = _create_exam(teacher)
    teacher.post(
        f"/teacher/exams/{exam['id']}/students/import",
        data={"csv": "firstname\nJane\n"},
        follow_redirects=True,
    )
    store.append_log(exam["id"], "Jane", "note", "manual entry")
    payload = teacher.get(
        f"/teacher/exams/{exam['id']}/data?since=0"
    ).get_json()
    assert any(
        issue["event"] == "note" and issue["message"] == "manual entry"
        for issue in payload["issues"]
    )


def test_zip_downloads_and_delete(teacher):
    exam = _create_exam(teacher)
    teacher.post(
        f"/teacher/exams/{exam['id']}/students/import",
        data={"csv": "firstname\nJane\n"},
        follow_redirects=True,
    )
    store.save_screenshot(exam["id"], "Jane", b"pngdata")

    single = teacher.get(f"/teacher/exams/{exam['id']}/student/Jane/download")
    assert single.status_code == 200
    with zipfile.ZipFile(io.BytesIO(single.data)) as archive:
        assert archive.namelist() == [
            "Jane/" + store.list_screenshots(exam["id"], "Jane")[0]["filename"]
        ]

    all_zip = teacher.get(f"/teacher/exams/{exam['id']}/download")
    with zipfile.ZipFile(io.BytesIO(all_zip.data)) as archive:
        assert len(archive.namelist()) == 1

    exam_dir = store.exam_dir(exam["id"])
    assert exam_dir.exists()
    teacher.post(f"/teacher/exams/{exam['id']}/delete", follow_redirects=True)
    assert not exam_dir.exists()
