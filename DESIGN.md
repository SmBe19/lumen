# Lumen Design

## Overview
Lumen is a tool for screen monitoring during exams. Students share their full screen on a website and the tool takes a screenshot in regular intervals. The screenshots are sent to a server. The teacher has an overview of all the screens, where they can see the current screenshots and view older screenshots.

## Config
The teacher can configure an exam key which the students will enter to join an exam.

The teacher can specify the screenshot interval, this can also be changed while the exam is already running.

The teacher can add a list of students which are taking an exam. This list can be imported by pasting a csv file. Once imported, a student just has a displayname. In the csv import, the following columns are available: firstname, lastname, displayname, class. At least one of firstname, lastname, displayname has to be specified, the rest is optional.

The teacher can specify the scale (0.01 - 1.00) of the screenshots to take (to reduce file size).

The teacher can start and stop the recording.

## Recording
To enter, a student enters the exam key. Then, they choose their name from a dropdown. Then, they screenshare their screen.

For recording, the students have to screen share their whole display. The tool then takes a screenshot in regular intervals as configured, scales them down, and sends this to the server. If the recording stops for some reason, a notification is displayed on the student machine as well as on the teacher machine.

If a student shares only a single window instead of the whole screen, this is rejected and the student is asked to share again.

When students try to leave the page while the recording is still running, this is prevented.

## Monitoring
The teacher has an overview of all current screenshots with the student names. When clicking on a student, they can view all old screenshots for that user.

A list of users in the exam which are not screen sharing is displayed.

A log is kept for each student which contains information about starting and stopping of recording, or any issues encountered for a student. The teacher can also manually add log entries to record any irregularities.

The screenshots of a single students or for all students can be downloaded as a ZIP-file.

## Login
Teachers need to login to configure exams. Students do not need to login.

## Backend
The backend is written with flask. For rendering the pages, jinja is used. uv is used for dependency management and as a build system.

All data is stored directly on disk (both exam config and the screenshots), no database is used. The config is not changed concurrently, so no locking is necessary there. The config can be kept in memory for some time and only needs to be reloaded from disk periodically (e.g. every 30 seconds).

## Frontend
The frontend is using vanilla JS. The design is very minimalistic (e.g. no gradients, rounded corners etc.), keeping css to a minimum.
