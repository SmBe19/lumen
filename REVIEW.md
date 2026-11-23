# Review Lumen

The application is not yet deployed, so the changes do not need to be backwards compatible.

- Importing the following csv fails:
    Name;Vorname;Klasse;Adresse;PLZ;Ort;EMail;Telefon
    User;Test;1A;"Beispielstrasse 42";4200;Bern;test.user@example.com;
- In the German and French translations, use formal you (Sie, Vous).
- When sharing the screen while the recording is not yet started, the student sees the following error message: "Die Aufnahme funktioniert derzeit nicht. Deine Lehrkraft muss sie neu starten.". This is not correct, it should not be an error. It should state something along the lines of that the recording is ready, but is currently not yet being recorded.
- The message "Die Aufnahme funktioniert." sounds weird. It should just say something that the screen is being recorded.
- "screen share track ended" is a weird error message to display in a notification for the teacher.
- Once a student starts sharing again, it still shows "Bildschirmfreigabe beendet. Bitte informiere deine Lehrkraft, damit die Aufnahme neu gestartet wird.".
- If the exam is currently not being recorded, we don't need to show a notification if screen sharing stops.
