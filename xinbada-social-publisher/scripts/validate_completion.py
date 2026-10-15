#!/usr/bin/env python3
"""Require one verified Facebook post, or report a validated dry-run accurately."""
import argparse
import sys
from pathlib import Path
from common import *
from validate_campaign import validate, require
from update_manifest import publication_evidence, frozen_content
from report_sheet import validate_reporting


def completion(path):
    path = Path(path).resolve()
    m = load_manifest(path)
    root = path.parent
    if m['mode'] == 'dry-run':
        require(not m['submission_history'] and m['channels']['facebook']['status'] == 'not_started', 'Dry-run must have no publication')
        require(m.get('reporting', {}).get('google_sheet', {}).get('status') in (None, 'not_started'), 'Dry-run must have no Sheets write')
        validate(path)
        return {'status': 'dry-run', 'checked_at': now(), 'published': False, 'manifest': str(path)}
    require(m['channels']['facebook']['status'] == 'published', 'Facebook is not verified published')
    frozen_content(path, m)
    validate(path, include_upload=within(root, m['artifacts']['upload']).exists())
    ev = publication_evidence(path, m, m['channels']['facebook']['url'])
    reporting = validate_reporting(path, m)
    return {'status': 'complete', 'checked_at': now(), 'published': True, 'facebook_url': ev['url'],
            'product_url': m['product_url'], 'manifest': str(path), 'verification_context': ev['verification_context'],
            'google_sheet': {'status': reporting['status'], 'url': reporting['url'], 'row_number': reporting['row_number']}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path)
    args = p.parse_args()
    evidence = args.manifest.resolve().parent / 'evidence/completion-validation.json'
    try:
        result = completion(args.manifest)
    except Exception as exc:
        write(evidence, {'status': 'incomplete', 'checked_at': now(), 'error': str(exc)})
        raise
    write(evidence, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
