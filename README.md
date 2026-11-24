# Lumen

Lumen is a tool for screen monitoring during exams. Students share their whole
screen on a website and the browser takes a screenshot in regular intervals.
Screenshots are scaled on the student machine and uploaded to a Flask server.
Teachers configure exams, watch the current screens live and browse the full
history for every student.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- A modern browser (Chrome/Edge/Firefox) for screen sharing

## Install

```bash
uv sync
```

## Create a teacher account

```bash
uv run lumen add-teacher alice
# or non-interactively:
uv run lumen add-teacher alice --password secret
```

Teacher passwords are hashed with Werkzeug and stored in
`data/teachers.json`. Existing accounts are updated when the command is
repeated. List accounts with `uv run lumen list-teachers`.

## Run

```bash
uv run lumen --host 0.0.0.0 --port 5000
```

Then open <http://localhost:5000/>.

For production (e.g. on a Herokuish based platform) a `Procfile` is included
that starts the app with [gunicorn](https://gunicorn.org/):

```
web: gunicorn -k gthread --threads 8 --bind 0.0.0.0:$PORT 'lumen.app:create_app()'
```

The threaded (`gthread`) worker is used because most work is blocking disk I/O
(saving and serving screenshots, scanning directories, zipping downloads), which
threads can run concurrently. Keep it to a single worker process: the on-disk
caches in `lumen.store` are per-process, so additional worker processes would
serve stale exam config (e.g. the `recording` flag) for up to 30 seconds.

Remember that browsers only allow `getDisplayMedia` in a secure context, so in
production serve Lumen over HTTPS (or use `localhost` for testing).

## Using Lumen

### Teacher

1. Log in at `/login`.
2. Create an exam on the *Exams* page. You can set the exam key, the screenshot
   interval and the scale (0.01 – 1.00).
3. Import students by pasting CSV with a header row using the columns
   `firstname` (or `vorname`), `lastname` (or `name`), `displayname` and
   `class` (or `klasse`, `kl`) in any order. Matching is case insensitive and
   at least one name column is required; otherwise the import reports an
   error. The display name is chosen in this order:
   `displayname`, `firstname lastname`, `firstname`, `lastname`, with
   ` (class)` appended when a class is given.
4. Press **Start recording**. Students may join at any time; screenshots are
   only accepted while recording is active.
5. Use the *Monitor* page for a live overview. It shows the latest screenshot
   per student, students who stopped sharing (no screenshot within four
   intervals), and warnings when a name seems to be used by more than one
   machine.
6. Click a student name to browse all historical screenshots and the
   per-student log, add manual log entries, delete the student, or download a
   ZIP (which also contains the `jsonl` log). The whole exam can be downloaded
   as a ZIP from the config or monitor page. Recording can also be started and
   stopped directly from the monitor page.

### Student

1. Open the site and enter the exam key.
2. Choose your name from the dropdown.
3. Allow notifications when asked (used to warn you if sharing stops).
4. Click **Start screen sharing** and pick your **entire screen**. Sharing a
   single window or tab is rejected. Once recording is started by the teacher,
   screenshots are uploaded automatically. Leaving the page while recording
   triggers a confirmation prompt.

## Data layout

Everything lives on disk; there is no database.

```
data/
  secret_key                  # Flask session secret (auto-generated)
  teachers.json               # username -> password hash
  exams/
    <exam id>/
      config.json             # key, interval, scale, recording, students
      screenshots/
        <cleaned name with _ instead of spaces>/<epoch_ms>_<token>.png
      logs/
        <cleaned name>.jsonl
```

Exam configuration is cached in memory for 30 seconds for the student
screens. Teacher pages always read the configuration from disk so they never
show stale data. Deleting an exam removes its directory and all screenshots.

## Tests

```bash
uv run pytest
```
