"""Tests for the on-disk store helpers."""

from lumen import store


def test_clean_dirname_removes_unsafe_characters_and_spaces():
    assert store.clean_dirname("Jane Doe (1a)") == "Jane_Doe_1a"
    assert " " not in store.clean_dirname("Jane Doe (1a)")
    assert store.clean_dirname("../../etc/passwd") == "etc_passwd"
    assert store.clean_dirname("") == "student"


def test_parse_student_csv_with_header_priority():
    students = store.parse_student_csv(
        "firstname,lastname,displayname,class\n"
        "Jane,Doe,,1a\n"
        "John,Smith,js,1b\n"
        ",,Maria,2a\n"
        "   ,   ,   ,2b\n"
    )
    assert [s["name"] for s in students] == [
        "Jane Doe (1a)",
        "js (1b)",
        "Maria (2a)",
    ]


def test_parse_student_csv_without_header_and_column_order():
    students = store.parse_student_csv("class,lastname,firstname\n1a,Doe,Jane\n")
    names = [s["name"] for s in students]
    assert names == ["Jane Doe (1a)"]


def test_parse_student_csv_accepts_alternative_column_names():
    students = store.parse_student_csv(
        "Vorname,NAME,KLASSE\nJane,Doe,1a\nJohn,Smith,1b\n"
    )
    assert [s["name"] for s in students] == [
        "Jane Doe (1a)",
        "John Smith (1b)",
    ]


def test_parse_student_csv_without_valid_columns_raises():
    import pytest

    with pytest.raises(ValueError):
        store.parse_student_csv("Jane,Doe\nJohn,Smith\n")


def test_parse_student_csv_with_semicolons_and_extra_columns():
    students = store.parse_student_csv(
        "Name;Vorname;Klasse;Adresse;PLZ;Ort;EMail;Telefon\n"
        'User;Test;1A;"Beispielstrasse 42";4200;Bern;test.user@example.com;\n'
    )
    assert [s["name"] for s in students] == ["Test User (1A)"]


def test_parse_student_csv_lastname_only():
    students = store.parse_student_csv("lastname\nDoe\n")
    assert [s["name"] for s in students] == ["Doe"]


def test_add_students_deduplicates_names_and_directories():
    exam = {"students": []}
    added = store.add_students(exam, [{"name": "A B"}, {"name": "A B"}, {"name": "A_B"}])
    assert added == 2
    dirs = [s["dir"] for s in exam["students"]]
    assert len(dirs) == len(set(d.lower() for d in dirs))
