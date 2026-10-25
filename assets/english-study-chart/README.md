# English Study Chart

This 600 × 300 SVG replaces the old English Progress card in the profile README.
It shows the last seven local calendar days (oldest to newest), daily OpenQuiz study
minutes and words, and the OpenQuiz streak. A dash means data has not been synced;
it is not treated as zero. The axis grows automatically for days over five hours.
The initial `data.json` uses the Oct 20–26 values shown in the user's OpenQuiz
browser console (Oct 26 had not been studied yet); it is not the sample data from
the ZIP. These historical times were measured before the presence-timer fix.

The PreMiD OpenQuiz presence syncs seven daily activity rows into the README near
23:30 local time. `.github/workflows/english-study-chart.yml` then runs at 23:45
Vietnam time, reads those rows, updates `data.json` and rebuilds the SVG using
Python's standard library. If the browser was not open for the OpenQuiz sync,
missing days stay unknown instead of being fabricated.
Streak is stored in the hidden `<!-- OPENQUIZ_STREAK:65 -->` README comment,
so it updates the chart without showing an extra line on the profile page.
The updater keeps previously recorded dates that have rolled off a short README
table; fresh README rows always replace older values for the same date.

To rebuild locally after the README is updated:

```bash
python3 scripts/update-english-study-chart.py
```

`daily_goal_hours`, `max_hours` (minimum axis height), and `bar_opacity` can be
adjusted in `data.json`. The script maintains the `days` and
`current_streak_days` fields from the README. No API calls are made by the script.
