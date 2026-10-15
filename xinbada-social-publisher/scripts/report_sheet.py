#!/usr/bin/env python3
"""Plan and verify Facebook-only Sheets reporting. No remote writes or social posting."""
from __future__ import annotations
import argparse
import fcntl
import sys
from zoneinfo import ZoneInfo
from common import *
from validate_campaign import require
from update_manifest import frozen_content, publication_evidence

SPREADSHEET_ID = '18iLpJ7bpDbJzxYtg0vsSOQxOR2e0KBuMI9C7LK0MhAw'
SHEET_URL = 'https://docs.google.com/spreadsheets/d/' + SPREADSHEET_ID + '/edit#gid=0'
SHEET_TITLE = 'social-auto-upload'
SHEET_NAME = '工作表1'
HEADERS = ['域名', '发布时间', '发布的站内链接', 'Facebook链接', 'LinkedIn链接']


def facebook_key(url):
    """Ignore tracking, host aliases and permalink/story/posts URL wrappers."""
    try:
        if not permalink(url):
            return None
        p = urlsplit(url)
        post_id = parse_qs(p.query)['story_fbid'][0] if p.path in ('/permalink.php', '/story.php') else p.path.rstrip('/').split('/')[-1]
        return PAGE_ID + ':' + post_id
    except (ValueError, TypeError, KeyError):
        return None


def plan(path):
    path = Path(path).resolve()
    m = load_manifest(path)
    require(m['mode'] == 'live', 'Dry-run cannot report to Google Sheets')
    require(m['channels']['facebook']['status'] == 'published', 'Facebook must be verified published before reporting')
    frozen_content(path, m)
    ev = publication_evidence(path, m, m['channels']['facebook']['url'])
    # A stable original verification timestamp avoids changing a backfill/retry to today's time.
    timestamp = datetime.fromisoformat(ev['checked_at'].replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Shanghai'))
    return {'spreadsheet_id': SPREADSHEET_ID, 'spreadsheet_title': SHEET_TITLE,
            'sheet_id': 0, 'sheet_name': SHEET_NAME, 'url': SHEET_URL, 'headers': HEADERS,
            'values': ['nutricdmo.com', timestamp.strftime('%Y-%m-%d %H:%M:%S'), '', ev['url'], ''],
            'time_basis': 'original_facebook_verification', 'dedupe_key': facebook_key(ev['url'])}


def decision(expected, rows):
    require(bool(rows) and rows[0] == HEADERS, 'Google Sheet headers mismatch')
    matches = []
    for number, row in enumerate(rows[1:], 2):
        # The connector returns interior blank cells as null and omits trailing blanks.
        values = [v if v is not None else '' for v in (row + [''] * 5)[:5]]
        if facebook_key(values[3]) == expected['dedupe_key']:
            matches.append((number, values))
    require(len(matches) <= 1, 'Duplicate Facebook links already exist; do not append')
    if not matches:
        return {'action': 'append'}
    number, values = matches[0]
    require(values[:3] == expected['values'][:3] and values[4] == '', 'Existing Facebook row conflicts; do not overwrite or append')
    return {'action': 'already_reported', 'row_number': number, 'values': values}


def checked_receipt(path, receipt):
    path = Path(path).resolve()
    expected = plan(path)
    for key in ('spreadsheet_id', 'spreadsheet_title', 'sheet_id', 'sheet_name', 'dedupe_key'):
        require(receipt.get(key) == expected[key], 'Reporting receipt target/key mismatch: ' + key)
    metadata = read(within(path.parent, receipt['metadata_file']))['structuredContent']
    require(metadata['spreadsheetId'] == SPREADSHEET_ID and metadata['properties']['title'] == SHEET_TITLE, 'Live spreadsheet metadata mismatch')
    sheets = [s['properties'] for s in metadata['sheets'] if s['properties']['sheetId'] == 0]
    require(len(sheets) == 1 and sheets[0]['title'] == SHEET_NAME, 'Live target sheet mismatch')
    row_count = sheets[0]['gridProperties']['rowCount']
    rows, next_row, hashes = [], 1, {}
    paths = receipt['readback_files']
    require(bool(paths) and len(paths) == len(set(paths)), 'Readback files missing or duplicated')
    for relative in paths:
        file = within(path.parent, relative)
        data = read(file)['structuredContent']
        match = re.fullmatch(r"'工作表1'!A(\d+):E(\d+)", data['range'])
        require(match is not None, 'Readback must cover A:E of the exact sheet')
        start, end = map(int, match.groups())
        require(start == next_row and start <= end <= row_count and (end-start+1)*5 <= 50000, 'Readback bounds incomplete or oversized')
        values = data.get('values', [])
        require(data.get('majorDimension') == 'ROWS' and len(values) <= end-start+1, 'Invalid readback rows')
        require(all(len(row) <= 5 and all(v is None or isinstance(v, str) for v in row) for row in values), 'Expected five text cells')
        rows.extend(values + [[] for _ in range(end-start+1-len(values))])
        next_row = end + 1
        hashes[relative] = sha(file)
    require(next_row == row_count+1, 'Readback must cover all current rows for Facebook deduplication')
    found = decision(expected, rows)
    require(found['action'] == 'already_reported' and receipt.get('row_number') == found['row_number'], 'Verified reporting row missing or wrong')
    checked = datetime.fromisoformat(receipt['checked_at'].replace('Z', '+00:00'))
    verified = datetime.fromisoformat(read(path.parent/'evidence/facebook-verification.json')['checked_at'].replace('Z', '+00:00'))
    require(checked.tzinfo is not None and verified <= checked <= datetime.now(timezone.utc), 'Reporting verification timestamp invalid')
    hashes[receipt['metadata_file']] = sha(within(path.parent, receipt['metadata_file']))
    return {**found, 'hashes': hashes}


def record(path, status='reported', error=None):
    path = Path(path).resolve()
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        expected = plan(path)
        m = load_manifest(path)
        require(status in ('reported', 'failed', 'blocked', 'uncertain'), 'Invalid reporting status')
        old = m.get('reporting', {}).get('google_sheet', {})
        require(old.get('status') != 'reported' or status == 'reported', 'Reported status is terminal')
        result = {'status': status, 'updated_at': now(), 'spreadsheet_id': SPREADSHEET_ID, 'url': SHEET_URL}
        if status == 'reported':
            receipt_path = path.parent/'evidence/google-sheet-verification.json'
            receipt = read(receipt_path)
            verified = checked_receipt(path, receipt)
            require(fresh(receipt['checked_at']), 'Reporting readback is stale')
            result.update(row_number=receipt['row_number'], dedupe_key=expected['dedupe_key'],
                          values=verified['values'], evidence_sha256=sha(receipt_path), source_hashes=verified['hashes'])
            if old.get('status') == 'reported':
                validate_reporting(path, m)
                return m
        else:
            require(bool(error), 'Reporting failure requires a reason')
            result['error'] = error
        m.setdefault('reporting', {})['google_sheet'] = result
        m.setdefault('reporting_history', []).append(result.copy())
        write(path, m)
        return m


def validate_reporting(path, m):
    path = Path(path).resolve()
    report = m.get('reporting', {}).get('google_sheet', {})
    require(report.get('status') == 'reported', 'Google Sheets reporting has not been verified')
    receipt_path = path.parent/'evidence/google-sheet-verification.json'
    require(report.get('evidence_sha256') == sha(receipt_path), 'Reporting receipt changed')
    verified = checked_receipt(path, read(receipt_path))
    require(report.get('spreadsheet_id') == SPREADSHEET_ID and report.get('url') == SHEET_URL and
            report.get('dedupe_key') == plan(path)['dedupe_key'] and
            report.get('source_hashes') == verified['hashes'] and
            report.get('row_number') == verified['row_number'] and report.get('values') == verified['values'], 'Reporting evidence or row changed')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--record', choices=('reported', 'failed', 'blocked', 'uncertain'))
    parser.add_argument('--error')
    args = parser.parse_args()
    result = record(args.manifest, args.record, args.error)['reporting']['google_sheet'] if args.record else plan(args.manifest)
    if not args.record:
        write(args.manifest.resolve().parent/'evidence/google-sheet-plan.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
