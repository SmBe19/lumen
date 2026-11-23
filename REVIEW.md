# Review Lumen

The application is not yet deployed, so the changes do not need to be backwards compatible.

- On the main page, the student login should be front and center. Remove the subtitle "Screen monitoring for exams". The teacher login only needs to be in the top right corner, the box in the middle can be removed.
- The default screenshot interval should be 10 second.
- The data directory should not contain spaces. Replace spaces by _.
- In the CSV import, if no valid columns are found, it should output an error instead of treating each line as a display name.
- Allow the following alternative column names for importing: "firstname": "vorname", "lastname": "name", "class": "klasse", "kl". Make sure this is case insensitive.
- Add the ability to delete single users.
- The title of the main page should be just "Lumen", not "Lumen - join an exam". Same for the page where students share their screen. On that page, indicate in the title whether the recording is currently working or not.
- After joining an exam, the different steps should not be shown at the same time. Only the currently relevant step should be shown.
- In step 2 when joining, add a disclaimer about data retention. State that the screen recording will be stored and retained until the exam has been corrected and returned to the class. At that point, the recordings will be deleted.
- In step 3 when joining, do not state the upload frequency. Only show whether the recording is working correctly or not.
- When I click "Stop", I get two notifications, there should only be one. In the notification there should be some call to action that they should notify the teacher who will then make sure the recording starts again.
- Only sharing a window is accepted. If possible, this should be rejected.
- Every time I go on the monitor page, I get a notification that the screen share track ended. I should only get one notification per instance where a student was sharing their screen but stopped. Also, the notifications should only appear if the state is recording.
- When selecting the name, there should be some explanation for why the notification permission is being requested next.
- All the student views should be available in English, German, and French. Use the browser language to determine the language to use. The teacher pages do not need to be translated.
- The downloaded ZIP-files should also include the jsonl log files.
- The scaling of the images does not always work. If I share directly from Firefox, the images are scaled correctly. However, if I select "use operating system settings" (which is needed for full screen sharing), no scaling is applied.
- Add a deployment option using gunicorn. Add a procfile specifying a web process which uses gunicorn to run the application. We will deploy using herokuish.
- The full log on the student view is not needed, only show the current status.
- When recording is enabled, there should be a confirmation before the "stop" button actually stops screen sharing. It should be as hard as possible to accidentally stop sharing the screen.
- The student page should hit the config endpoint at most every 10 seconds. Also add some jitter to spread the requests.
- `get_exam_by_key` should also use a cache, this should not hit the disk every time. All the endpoints which are requested from the students in a regular interval should be as fast as possible, so only access the disk if absolutely necessary.
- On the monitor page, clicking on a screenshot should show the screenshot in a big overlay, clicking on the overlay then closes it again. To access student details, one needs to click on the username.
- On the monitor page, the issues should also include manually added entries.
- It should be possible to start/stop the recording from the monitor page.
- Not all buttons in the admin interface have the same padding, they should be consistent.
