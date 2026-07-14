# Excluded subjects per child — design

Date: 2026-07-14
Status: approved

## Problem

Shared timetable slots (religion `k/ev/eth`, `DaZ-plus7/intf`) produce
substitution-plan rows for every group in the slot, but each child only
attends one group. Rows for the other groups (e.g. Ethik, Latein,
DaZ-plus7) are noise: they show up in the console, in
`results/dsb_results.json`, and trigger notifications.

## Decisions (validated with user)

- **Per child**: each entry in `config.json` `children` gets an optional
  `excluded_subjects` list.
- **Filter everywhere**: excluded entries are dropped before printing,
  saving, and diffing — they never reach the console, the saved JSON, or
  notifications.
- **Match by code or full name**: a term matches when it equals, case-
  insensitively, either the plan entry's subject code (`eth`, `l`,
  `DaZ-plus7`) or its mapped full name (`Ethik`, `Latein`). Exact
  equality only — no substring matching, so `"l"` (Latein) does not
  affect `lint`/`intl`.
- Matching is against the **plan's** subject, not the regular-timetable
  slot name: "DaZ-plus7 canceled" is dropped, "intf canceled" is kept.

## Design

- Config: `{"name": "Diego", "class": "7d", "schedule": "data/7d.json",
  "excluded_subjects": ["Ethik", "Latein", "DaZ-plus7"]}`.
- At load time derive `EXCLUDED_BY_CLASS` (class lowercased → set of
  lowercased terms), alongside the existing `CLASS_TO_CHILD` /
  `TARGET_CLASSES` derivations.
- New pure function `filter_excluded_subjects(results,
  excluded_by_class=None)` over the `{date: {class: [entries]}}`
  structure; drops matching entries and prunes classes/dates left empty.
- Called once in `main()`, right after `format_results` and before
  `print_summary` / diff / save. Single choke point keeps console, JSON
  and notifications consistent.
- `config.example.json` documents the new field.

## Testing

Unit tests (offline): exclusion by code, by full name, case-insensitive,
no substring match, per-class independence (excluded in 7d, kept in 7e),
pruning of emptied classes/dates, and pass-through when no exclusions
are configured.
