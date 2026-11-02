# Schedule Overlap

Check a prepared CSV schedule for overlapping intervals assigned to the same
resource. Files stay on the machine running the command. Python 3.10+; no packages.

Run from this directory:

```sh
python3 schedule_overlap.py example.csv
```

The included synthetic schedule reports one overlap: data rows 1 and 2.
Exit status is 1 for overlaps, 0 for no overlaps, 2 for invalid/unreadable input.
Do not use `&&` to handle an overlap result as if it were a successful clean check.

Supply exactly `resource,start,end` headers in that order. Every row represents
one occupied interval. Timestamps use `YYYY-MM-DDTHH:MM:SSZ` or an explicit numeric
offset such as `2026-11-03T10:00:00+01:00`. End must follow start. Resources match
exactly and are case sensitive. Surrounding resource whitespace is rejected.
Intervals touching at an endpoint do not overlap. Reported row positions count
data records, starting at 1, excluding the header (not physical multiline lines).

This is a prepared-schedule checker, not an ICS reader, calendar export adapter,
availability service or booking system. Convert exports explicitly before use;
there is no direct Google/Outlook export compatibility claim. Recurring events
must already be expanded. Resolve timezones/daylight-saving transitions before
creating the file. No timezone names, floating times, all-day semantics, tentative
status, cancelled events, travel buffers or multi-resource row expansion.
Every row is treated as occupied. Unknown `-00:00` offsets are rejected.

UTF-8 with optional BOM; maximum 2 MB and 2,000 records. Dense schedules can
produce many pairs. Output contains row positions/counts, not resource names.
Reports still reveal schedule structure; keep them private when appropriate.
The tool reads the input without modifying it. It does not reserve resources
or prevent another person changing a schedule after a check.

Run synthetic checks: `python3 -m unittest -v`. Preview tested on Linux with
Python 3.12.15. Other platforms and Python versions have not been tested.
Free, MIT-licensed source from Gong LLC.
