"""Translations for the student facing views.

Only the student pages are translated. The browser language is negotiated
from the ``Accept-Language`` header (falling back to English).
"""

from __future__ import annotations

from flask import request

LANGUAGES = ("en", "de", "fr")
DEFAULT_LANGUAGE = "en"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "base.teacher_login": "Teacher login",
        "index.title": "Lumen",
        "index.heading": "Lumen",
        "index.join_heading": "Join an exam",
        "index.join_hint": "Enter the exam key you received from your teacher.",
        "index.exam_key": "Exam key",
        "index.join_button": "Join exam",
        "student.title_recording": "Lumen - recording",
        "student.title_not_recording": "Lumen - not recording",
        "student.no_students": "No students have been added to this exam yet. Ask your teacher.",
        "student.step1_heading": "1. Choose your name",
        "student.name_label": "Name",
        "student.name_placeholder": "-- select your name --",
        "student.continue": "Continue",
        "student.notify_explanation": "Your browser will now ask for permission to show notifications. This allows us to warn you immediately if screen sharing stops while the exam is being recorded.",
        "student.step2_heading": "2. Share your whole screen",
        "student.step2_body": "You must share your entire screen. Sharing a single window or browser tab is not accepted.",
        "student.step2_disclaimer": "The screen recording will be stored and retained until the exam has been corrected and returned to the class. At that point, the recordings will be deleted.",
        "student.start_sharing": "Start screen sharing",
        "student.stop": "Stop",
        "student.step3_heading": "3. Recording",
        "student.status_not_sharing": "Not sharing.",
        "js.select_name_first": "Please select your name first.",
        "js.sharing_not_available": "Screen sharing is not available in this browser or context (it requires a secure HTTPS connection).",
        "js.share_cancelled": "Screen sharing was cancelled.",
        "js.could_not_start": "Could not start screen sharing: %(error)s",
        "js.wrong_surface": "You shared a %(surface)s instead of your entire screen. Please share your whole display.",
        "js.share_ended": "Screen sharing stopped. Please notify your teacher so they can restart the recording.",
        "js.recording_started": "Recording started.",
        "js.recording_stopped": "Recording stopped by the teacher.",
        "js.status_recording_ok": "Recording is working.",
        "js.status_recording_stopped": "Recording is currently not working. Your teacher needs to start it again.",
        "js.notify_stopped_title": "Lumen: screen sharing stopped",
        "js.notify_stopped_body": "Your screen is no longer being recorded. Notify your teacher so they can restart the recording.",
        "js.stop_confirm": "Are you sure you want to stop sharing your screen? Recording is currently active. If you stop, notify your teacher immediately so they can restart it.",
        "js.leave_warning": "Recording is still running. Are you sure you want to leave?",
        "not_found.title": "Unknown exam",
        "not_found.heading": "Unknown exam key",
        "not_found.body": "This exam key does not match any exam.",
        "not_found.back": "Back to start",
    },
    "de": {
        "base.teacher_login": "Lehrer-Anmeldung",
        "index.title": "Lumen",
        "index.heading": "Lumen",
        "index.join_heading": "Einer Prüfung beitreten",
        "index.join_hint": "Gib den Prüfungsschlüssel ein, den du von deiner Lehrkraft erhalten hast.",
        "index.exam_key": "Prüfungsschlüssel",
        "index.join_button": "Beitreten",
        "student.title_recording": "Lumen - Aufnahme läuft",
        "student.title_not_recording": "Lumen - Aufnahme gestoppt",
        "student.no_students": "Dieser Prüfung wurden noch keine Schülerinnen und Schüler hinzugefügt. Frage deine Lehrkraft.",
        "student.step1_heading": "1. Namen auswählen",
        "student.name_label": "Name",
        "student.name_placeholder": "-- Namen auswählen --",
        "student.continue": "Weiter",
        "student.notify_explanation": "Dein Browser fragt dich jetzt nach der Erlaubnis, Benachrichtigungen anzuzeigen. So können wir dich sofort warnen, wenn die Bildschirmfreigabe während der Aufnahme stoppt.",
        "student.step2_heading": "2. Ganzen Bildschirm teilen",
        "student.step2_body": "Du musst deinen gesamten Bildschirm teilen. Das Teilen eines einzelnen Fensters oder Browser-Tabs wird nicht akzeptiert.",
        "student.step2_disclaimer": "Die Bildschirmaufnahme wird gespeichert und aufbewahrt, bis die Prüfung korrigiert und der Klasse zurückgegeben wurde. Danach werden die Aufnahmen gelöscht.",
        "student.start_sharing": "Bildschirmfreigabe starten",
        "student.stop": "Stoppen",
        "student.step3_heading": "3. Aufnahme",
        "student.status_not_sharing": "Keine Freigabe.",
        "js.select_name_first": "Bitte wähle zuerst deinen Namen aus.",
        "js.sharing_not_available": "Bildschirmfreigabe ist in diesem Browser oder Kontext nicht verfügbar (erfordert eine sichere HTTPS-Verbindung).",
        "js.share_cancelled": "Bildschirmfreigabe wurde abgebrochen.",
        "js.could_not_start": "Bildschirmfreigabe konnte nicht gestartet werden: %(error)s",
        "js.wrong_surface": "Du hast %(surface)s statt deines gesamten Bildschirms geteilt. Bitte teile deinen ganzen Bildschirm.",
        "js.share_ended": "Bildschirmfreigabe beendet. Bitte informiere deine Lehrkraft, damit die Aufnahme neu gestartet wird.",
        "js.recording_started": "Aufnahme gestartet.",
        "js.recording_stopped": "Die Aufnahme wurde von der Lehrkraft gestoppt.",
        "js.status_recording_ok": "Die Aufnahme funktioniert.",
        "js.status_recording_stopped": "Die Aufnahme funktioniert derzeit nicht. Deine Lehrkraft muss sie neu starten.",
        "js.notify_stopped_title": "Lumen: Bildschirmfreigabe beendet",
        "js.notify_stopped_body": "Dein Bildschirm wird nicht mehr aufgezeichnet. Informiere deine Lehrkraft, damit die Aufnahme neu gestartet wird.",
        "js.stop_confirm": "Möchtest du die Bildschirmfreigabe wirklich beenden? Die Aufnahme läuft gerade. Informiere danach sofort deine Lehrkraft, damit sie neu gestartet werden kann.",
        "js.leave_warning": "Die Aufnahme läuft noch. Möchtest du die Seite wirklich verlassen?",
        "not_found.title": "Unbekannte Prüfung",
        "not_found.heading": "Unbekannter Prüfungsschlüssel",
        "not_found.body": "Dieser Prüfungsschlüssel passt zu keiner Prüfung.",
        "not_found.back": "Zurück zum Start",
    },
    "fr": {
        "base.teacher_login": "Connexion enseignant",
        "index.title": "Lumen",
        "index.heading": "Lumen",
        "index.join_heading": "Rejoindre un examen",
        "index.join_hint": "Saisis la clé d'examen que tu as reçue de ton enseignant.",
        "index.exam_key": "Clé d'examen",
        "index.join_button": "Rejoindre",
        "student.title_recording": "Lumen - enregistrement en cours",
        "student.title_not_recording": "Lumen - enregistrement arrêté",
        "student.no_students": "Aucun élève n'a encore été ajouté à cet examen. Demande à ton enseignant.",
        "student.step1_heading": "1. Choisis ton nom",
        "student.name_label": "Nom",
        "student.name_placeholder": "-- choisis ton nom --",
        "student.continue": "Continuer",
        "student.notify_explanation": "Ton navigateur va maintenant demander l'autorisation d'afficher des notifications. Cela nous permet de t'avertir immédiatement si le partage d'écran s'arrête pendant l'enregistrement.",
        "student.step2_heading": "2. Partage tout ton écran",
        "student.step2_body": "Tu dois partager ton écran entier. Le partage d'une seule fenêtre ou d'un onglet n'est pas accepté.",
        "student.step2_disclaimer": "L'enregistrement d'écran sera conservé jusqu'à ce que l'examen soit corrigé et rendu à la classe. À ce moment-là, les enregistrements seront supprimés.",
        "student.start_sharing": "Démarrer le partage d'écran",
        "student.stop": "Arrêter",
        "student.step3_heading": "3. Enregistrement",
        "student.status_not_sharing": "Aucun partage.",
        "js.select_name_first": "Veuillez d'abord choisir votre nom.",
        "js.sharing_not_available": "Le partage d'écran n'est pas disponible dans ce navigateur ou ce contexte (il nécessite une connexion HTTPS sécurisée).",
        "js.share_cancelled": "Le partage d'écran a été annulé.",
        "js.could_not_start": "Impossible de démarrer le partage d'écran : %(error)s",
        "js.wrong_surface": "Tu as partagé %(surface)s au lieu de tout ton écran. Veuillez partager tout ton écran.",
        "js.share_ended": "Le partage d'écran s'est arrêté. Préviens ton enseignant pour qu'il relance l'enregistrement.",
        "js.recording_started": "Enregistrement démarré.",
        "js.recording_stopped": "L'enregistrement a été arrêté par l'enseignant.",
        "js.status_recording_ok": "L'enregistrement fonctionne.",
        "js.status_recording_stopped": "L'enregistrement ne fonctionne pas actuellement. Ton enseignant doit le relancer.",
        "js.notify_stopped_title": "Lumen : partage d'écran arrêté",
        "js.notify_stopped_body": "Ton écran n'est plus enregistré. Préviens ton enseignant pour qu'il relance l'enregistrement.",
        "js.stop_confirm": "Veux-tu vraiment arrêter le partage d'écran ? L'enregistrement est en cours. Préviens immédiatement ton enseignant pour qu'il puisse le relancer.",
        "js.leave_warning": "L'enregistrement est toujours en cours. Veux-tu vraiment quitter la page ?",
        "not_found.title": "Examen inconnu",
        "not_found.heading": "Clé d'examen inconnue",
        "not_found.body": "Cette clé d'examen ne correspond à aucun examen.",
        "not_found.back": "Retour au départ",
    },
}


def negotiate(accept_languages) -> str:
    """Pick the best supported language for the given request languages."""
    if accept_languages is None:
        return DEFAULT_LANGUAGE
    try:
        match = accept_languages.best_match(list(LANGUAGES))
    except Exception:  # pragma: no cover - defensive
        return DEFAULT_LANGUAGE
    return match or DEFAULT_LANGUAGE


def current_language() -> str:
    try:
        return negotiate(request.accept_languages)
    except RuntimeError:
        return DEFAULT_LANGUAGE


def t(lang: str, key: str, **kwargs: object) -> str:
    table = TRANSLATIONS.get(lang) or TRANSLATIONS[DEFAULT_LANGUAGE]
    text = table.get(key) or TRANSLATIONS[DEFAULT_LANGUAGE].get(key) or key
    if kwargs:
        return text % kwargs
    return text


def student_strings(lang: str) -> dict[str, str]:
    """Return the full translation table used by the student JavaScript."""
    return dict(TRANSLATIONS.get(lang) or TRANSLATIONS[DEFAULT_LANGUAGE])
