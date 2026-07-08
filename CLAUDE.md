# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-script Python tool (`dsb_finder.py`) that checks the DSB (Digitales Schwarzes Brett) substitution plan of a German school and reports teacher substitutions and canceled lessons for two classes (7d = Diego, 7e = Mateo). Personal/family tool, also run on Android via Termux.

## Running

```bash
pip install beautifulsoup4 requests urllib3
python dsb_finder.py
```

Tests (stdlib `unittest`, offline via a fake session):

```bash
python -m unittest test_dsb_finder -v
```

There is no linter config and no requirements.txt — dependencies are only documented in README.md.

On legacy Windows consoles (cp1252) unsupported characters degrade to `?` (stdout is reconfigured with `errors="replace"` at startup); run with `PYTHONUTF8=1` to get the full emoji output.

## Data flow (dsb_finder.py)

1. **Auth + fetch** (`fetch_dsb_data`): GET to `mobileapi.dsbcontrol.de/authid` with hardcoded credentials returns an auth ID, then `/dsbtimetables` returns JSON with a tree of plan entries (`Childs[].Detail` = URLs to HTML pages). TLS verification is deliberately disabled (`verify=False`).
2. **Scrape** (`extract_timetable_info` → `extract_class_info`): each plan URL is an HTML page (`table.mon_list`) parsed with BeautifulSoup. Rows with `<strike>` in the subject cell indicate cancellation. A regex fallback handles malformed rows without proper cells. Raw responses are dumped to `debug/`. **A single day's plan spans several `subst_NNN.htm` pages that all share the same `mon_title` date**, so results must be merged per date/class across pages, never assigned per page (this was a real lost-entries bug). Debug dumps are keyed by plan title plus the page name from the URL (`subst_001`, `subst_002`, ...), one file per page.
3. **Enrich** (`enhance_with_schedule`, `enhance_entry_details`): entries are cross-referenced with the local regular timetables (`data/7d.json`, `data/7e.json`), `data/teacher_map.json` (code → [name, subject]) and `data/subject_mapping.json` (code → full subject name). A class counts as canceled only when both teacher cells are `<strike>`-d and equal, or the Text column matches ENTFALL/Ausfall/cancel; the same teacher without strikes means a subject/room change, not a cancellation.
4. **Output** (`format_results`, `print_summary`, `save_results`): deduplicated, grouped by date then by child, printed to console (mobile-friendly format with emoji), and saved to `results/dsb_results.json`.
5. **Notify** (`diff_new_entries`, `compose_notification`, `send_notification`): the run is compared against the previous `results/dsb_results.json` (loaded before overwriting it) and only genuinely new entries trigger a notification, sent via ntfy.sh or termux-notification per the `notify` block in `config.json` (`method: "none"` disables it).

## Configuration

All per-family configuration lives in `config.json` (gitignored — template in `config.example.json`): DSB credentials, children (name + class + schedule file), and notification settings. Everything else is derived from it: target-class variants ("7d"/"7D"/"7.d"/"7.D"), the child-name mapping in the summary, the malformed-row fallback regex, and which schedule files load. Changing the school year means editing `config.json` and providing the new schedule JSONs. Credentials can also come from `DSB_USERNAME`/`DSB_PASSWORD` env vars, which take precedence over the file. Old-year schedules are moved to `_archive/`.

## Data file conventions

- Schedule JSONs use Spanish keys: `clase`, `eventos`, `dia` (1=Monday…5=Friday), `periodo`, `asignatura` (subject code), `aula`. Shared lessons use `/` separators (e.g. `"sw/sm"`, `"TH4/TH2"`).
- Day names, subjects, and teacher codes are German (from the school); user-facing console output is Spanish; code is English.
- `subject_mapping.json` keys are matched case-insensitively (normalized to lowercase at load); `teacher_map.json` keys are teacher codes matched exactly as they appear in the plan (usually uppercase).

## Generated files

`debug/` and `results/` are regenerated on every run and gitignored — never commit their contents.
