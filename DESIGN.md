# Lumen Design

## Overview
Lumen is a tool for screen monitoring during exams. Students share their full screen on a website and the tool takes a screenshot in regular intervals. The screenshots are sent to a server. The teacher has an overview of all the screens, where they can see the current screenshots and view older screenshots.

## Config
The teacher can configure an exam key which the students will enter to join an exam.

The teacher can specify the screenshot interval, this can also be changed while the exam is already running.

The teacher can add a list of students which are taking an exam. This list can be imported by pasting a csv file. Once imported, a student just has a displayname. In the csv import, the following columns are available: firstname, lastname, displayname, class. At least one of firstname, lastname, displayname has to be specified, the rest is optional. The imported displayname is, in order of priority, "{displayname}", "{firstname} {lastname}", "{firstname}", "{lastname}", appended with " ({class})" if available.

The teacher can specify the scale (0.01 - 1.00) of the screenshots to take (to reduce file size).

The teacher can start and stop the recording. Only if the recording is active, the student machines send screenshots to the server. The students can join an exam even if the recording is not running.

A teacher can create multiple exams and have them running at the same time.

An exam only has two states, recording or not recording. Before or after the exam is not distinguished.

## Recording
To enter, a student enters the exam key. Then, they choose their name from a dropdown. Then, they screenshare their screen.

For recording, the students have to screen share their whole display. The tool then takes a screenshot in regular intervals as configured, scales them down, and sends this to the server. If the recording stops for some reason, a notification is displayed on the student machine as well as on the teacher machine. For the notification, the browser permission is requested at the start when joining an exam.

The screenshots are stored an PNG files. The scaling happens on the client to save on bandwidth.

If a student shares only a single window instead of the whole screen, this is rejected and the student is asked to share again.

When students try to leave the page while the recording is still running, a leave warning is shown.

Multiple machines selecting the same name is fine. If the server receives screenshots from multiple machines (e.g. it receives more screenshots than expected based on the interval), a warning is shown to the teacher.

If the server receives screenshots while the exam is not in recording state, the screenshots are discarded.

## Monitoring
The teacher has an overview of all current screenshots with the student names. When clicking on a student, they can view all old screenshots for that user.

A list of users in the exam which are not screen sharing (no screenshot within the last 4 intervals) is displayed.

A log is kept for each student which contains information about starting and stopping of recording, or any issues encountered for a student. The teacher can also manually add log entries to record any irregularities.

The screenshots of a single students or for all students can be downloaded as a ZIP-file.

When an exam is deleted, all the screenshots stored for that exam are deleted as well.

## Login
Teachers need to login to configure exams. Students do not need to login, they only need the exam key. The exam key only allows to submit screenshots and read the config necessary for the screenshots (e.g. the interval). To view the overview of all screenshots or change configs, the teacher needs to be logged in.

Teacher accounts are added with a cli utility to hash the passwords and add it to the file.

## Backend
The backend is written with flask. For rendering the pages, jinja is used. uv is used for dependency management and as a build system.

All data is stored directly on disk (both exam config and the screenshots), no database is used. The config is not changed concurrently, so no locking is necessary there. The config can be kept in memory for some time and only needs to be reloaded from disk periodically (e.g. every 30 seconds). However, to serve the config page for the teacher, the config always needs to be read from disk to ensure no stale data is displayed.

For the screenshots, a cleaned version of the displayname of a student is used as the directory name. Each exam has a separate directory, within which the screenshot directories reside.

## Frontend
The frontend is using vanilla JS. The design is very minimalistic (e.g. no gradients, rounded corners etc.), keeping css to a minimum.
