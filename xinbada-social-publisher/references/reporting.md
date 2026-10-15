# Mandatory Google Sheets reporting

Every successful authorized live run includes one audit row after Facebook has been verified.
No extra routine approval is needed. Reporting-only repair of a specified published run starts
here and must never create another Facebook post or reset its submission history.

## Destination and five-cell mapping

- Spreadsheet: [social-auto-upload](https://docs.google.com/spreadsheets/d/18iLpJ7bpDbJzxYtg0vsSOQxOR2e0KBuMI9C7LK0MhAw/edit#gid=0).
- Spreadsheet ID: `18iLpJ7bpDbJzxYtg0vsSOQxOR2e0KBuMI9C7LK0MhAw`.
- Sheet: `工作表1`, sheetId `0`; re-read live metadata and headers before any write.
- Headers A:E: `域名`, `发布时间`, `发布的站内链接`, `Facebook链接`, `LinkedIn链接`.
- Values: `nutricdmo.com`, original Facebook verification time in Asia/Shanghai formatted
  `YYYY-MM-DD HH:mm:ss`, `""`, verified Facebook permalink, `""`.

C and E must be genuinely empty. Do not insert a product-source URL, `不适用`, `N/A`, spaces,
or invented website/LinkedIn links. Product source remains in the manifest and local report.
The time uses the original `facebook-verification.json.checked_at` as a documented approximation
of publication time, not the time of a later reporting retry/backfill. Never rewrite that original
verification merely to update the audit timestamp.

## Read, deduplicate, write and verify

1. Load `google-drive:google-sheets` and its required references. Run
   `python3 scripts/report_sheet.py MANIFEST` to create `evidence/google-sheet-plan.json`.
   This validates the already-published Facebook evidence and produces the exact row and dedupe key.
   No helper here performs remote writes. Dry-run creates no audit row and cannot invoke reporting.
2. Read metadata with the Drive connector; verify exact spreadsheet title, sheet ID/title and
   five headers. Save the unmodified result, including `structuredContent`, as
   `evidence/google-sheet-metadata.json`. A mismatch blocks reporting without changing structure.
3. Read all current A:E rows in bounded chunks of at most 10,000 rows (50,000 cells) each, using
   exact sheet name and grid row count from metadata. Do not use whole-column unbounded reads or
   infer absence from a truncated search. Ignore trailing empty rows, not populated rows.
   `report_sheet.decision(plan, rows)` verifies headers and compares Facebook links. It ignores
   tracking parameters, accepted host aliases, and permalink/story/posts wrappers for the same
   post identifier. Never deduplicate by domain, product URL or website column.
4. If exactly one existing row matches the Facebook link and all five values (allowing equivalent
   Facebook URL spelling), reuse it. If duplicated or conflicting, mark reporting `blocked` and
   do not append or overwrite. Different opaque/numeric post IDs cannot be assumed equivalent;
   if an alternate URL might refer to the same post, reconcile through the visible post first.
5. If absent, inspect the populated edge and prospective target with `get_spreadsheet_cells`
   (values, formats, formulas, validation and chips). Preserve the sheet's native row structure.
   For a plain literal log, append one complete row with intended formatting via `appendCells`
   so another publisher's concurrent append is not overwritten; include blank cell data for C/E.
   For structured rows follow the Google Sheets native-row recipe. Never copy old row-specific
   hyperlinks or broaden formatting to the whole sheet. Recheck dedupe immediately before writing.
6. Read metadata and all bounded A:E chunks again after the write (or when reusing an existing row).
   Save raw results including `structuredContent` as `evidence/google-sheet-readback-01.json`, etc.
   Inspect the actual row's native cell data and render. Verify exactly one matching Facebook row,
   the domain/time, genuinely empty C/E and unchanged neighbors. Save the receipt below.
7. Run `python3 scripts/report_sheet.py MANIFEST --record reported`, then
   `python3 scripts/validate_completion.py MANIFEST`. The guard requires reporting evidence and
   binds its hashes to `reporting.google_sheet`; a Facebook-only success is no longer complete.

Receipt `evidence/google-sheet-verification.json`:

```json
{
  "spreadsheet_id": "18iLpJ7bpDbJzxYtg0vsSOQxOR2e0KBuMI9C7LK0MhAw",
  "spreadsheet_title": "social-auto-upload",
  "sheet_id": 0,
  "sheet_name": "工作表1",
  "dedupe_key": "COPY FROM google-sheet-plan.json",
  "checked_at": "CURRENT ISO8601 WITH TIMEZONE AFTER READBACK",
  "row_number": 60,
  "metadata_file": "evidence/google-sheet-metadata.json",
  "readback_files": ["evidence/google-sheet-readback-01.json"]
}
```

The row number above is illustrative; always obtain the actual row from live readback.
Chunk ranges must cover A1:E through the current grid's final row, contiguous and in order.
Missing trailing empty cells are normalized to empty strings for five-cell comparison.

## Recovery

For a definite reporting error, use `--record failed|blocked --error TEXT`; for uncertain remote
write outcome, use `--record uncertain --error TEXT`. Search/read the live Facebook-link column
before any retry. Never append speculatively or replay a verified row. A missing confirmation
does not mean the write failed. Existing Facebook status, URLs, artifacts and submission history
stay intact. Report social success and reporting failure separately, then resume only reporting
when authorized. Do not start a new publishing run to repair a report.
