#!/usr/bin/env python3
"""Record Facebook outcomes with permanent submission history; never publish remotely."""
from __future__ import annotations
import argparse
import fcntl
import sys
from pathlib import Path
from common import *
from validate_campaign import validate, require


def publication_evidence(path, m, url):
    root = Path(path).parent
    require(permalink(url), 'Not an acceptable Facebook post permalink for the target page')
    require(bool(m['submission_history']), 'No recorded submission')
    ev = read(root / 'evidence/facebook-verification.json')
    require(ev.get('url') == url and ev.get('page_id') == PAGE_ID and ev.get('author_page_id') == PAGE_ID, 'Published URL or author identity mismatch')
    copy_path = within(root, m['artifacts']['copy'])
    legacy = legacy_product_link(m, copy_path)
    link_check = 'product_link_matches' if legacy else NO_WEBSITE_LINKS
    if not legacy:
        require(not WEBSITE_LINK.search(copy_path.read_text(encoding='utf-8')), 'Social copy must not contain website links or bare domains')
    for key in ('text_matches', 'image_matches', link_check, 'published_visible'):
        require(ev.get(key) is True, 'Publication verification missing: ' + key)
    require(ev.get('copy_sha256') == sha(within(root, m['artifacts']['copy'])) and ev.get('social_sha256') == sha(within(root, m['artifacts']['social'])), 'Publication evidence hashes are stale')
    require(bool(ev.get('verification_context')), 'Verification context missing')
    checked = datetime.fromisoformat(ev['checked_at'].replace('Z', '+00:00'))
    submitted = datetime.fromisoformat(m['submission_history'][-1]['at'])
    require(checked.tzinfo is not None and submitted <= checked <= datetime.now(timezone.utc), 'Verification must follow submission')
    screenshot(root, ev['screenshot'])
    return ev


def frozen_content(path, m):
    if not m['submission_history']:
        return
    root = Path(path).parent
    hashes = m['submission_history'][0]['hashes']
    for key, expected in hashes.items():
        rel = {'content_review': 'evidence/content-review.json', 'image_review': 'evidence/image-review.json'}.get(key, m['artifacts'].get(key))
        artifact = within(root, rel)
        if key == 'upload' and m['channels']['facebook']['status'] == 'published' and not artifact.exists():
            continue
        require(sha(artifact) == expected, 'Submitted artifact changed: ' + key)


def update(path, status, url=None, error=None, submission_started=False):
    path = Path(path).resolve()
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        m = load_manifest(path)
        root = path.parent
        old = m['channels']['facebook']
        require(m.get('candidate_status') != 'rejected', 'Cannot publish a rejected candidate')
        if old['status'] == 'published':
            require(status == 'published' and url == old['url'] and not submission_started, 'Published status is terminal')
            return m
        require(not url or status == 'published', 'Only a verified published outcome accepts a URL')
        require(not submission_started or status == 'pending', 'Submission marker requires pending status')
        require(status != 'pending' or submission_started, 'Pending requires a permanent submission marker')
        if status in ('pending', 'published', 'uncertain'):
            require(m['mode'] == 'live', 'Dry-run cannot enter a publishing state')
        if status == 'uncertain':
            require(bool(m['submission_history']), 'Uncertain requires a prior submission')
        if submission_started:
            require(len(m['submission_history']) < 2, 'At most one retry is allowed')
            frozen_content(path, m)
            result = validate(path)
            pre = read(root / 'evidence/preflight.json')
            require(pre.get('page_id') == PAGE_ID and pre.get('page_url') == FACEBOOK, 'Preflight target mismatch')
            require(fresh(pre['checked_at']) and bool(pre.get('observed_page_name')), 'Preflight is stale or page name missing')
            for key in ('active_identity_verified', 'can_create_post', 'preview_verified'):
                require(pre.get(key) is True, 'Preflight missing: ' + key)
            require(pre.get('copy_sha256') == result['hashes']['copy'] and pre.get('upload_sha256') == result['hashes']['upload'], 'Preview hashes are stale')
            screenshot(root, pre['screenshot'])
            if m['submission_history']:
                reconcile = read(root / 'evidence/reconciliation.json')
                require(reconcile.get('page_id') == PAGE_ID and reconcile.get('verdict') == 'not_published' and fresh(reconcile['checked_at']), 'Retry requires fresh non-publication reconciliation')
                require(datetime.fromisoformat(reconcile['checked_at']) > datetime.fromisoformat(m['submission_history'][-1]['at']), 'Reconciliation predates submission')
                for key in ('published_checked', 'scheduled_checked', 'drafts_checked'):
                    require(reconcile.get(key) is True, 'Reconciliation missing: ' + key)
                require(bool(reconcile.get('notes')), 'Reconciliation explanation missing')
                screenshot(root, reconcile['screenshot'])
                # Preserve the first preflight and every reconciliation in submission history.
            m['submission_history'].append({'at': now(), 'copy_policy': result['copy_policy'], 'hashes': result['hashes'], 'preflight': pre,
                                            'reconciliation': reconcile if len(m['submission_history']) else None})
            write(root / 'evidence/campaign-validation.json', result)
        if status == 'published':
            frozen_content(path, m)
            publication_evidence(path, m, url)
        m['channels']['facebook'] = {'status': status, 'updated_at': now()}
        if url:
            m['channels']['facebook']['url'] = url
        if error:
            m['channels']['facebook']['error'] = error
        m['history'].append({'at': now(), 'status': status, 'url': url, 'error': error, 'submission_started': submission_started})
        write(path, m)
        return m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path)
    p.add_argument('--status', required=True, choices=('pending', 'published', 'blocked', 'failed', 'uncertain'))
    p.add_argument('--url')
    p.add_argument('--error')
    p.add_argument('--submission-started', action='store_true')
    a = p.parse_args()
    m = update(a.manifest, a.status, a.url, a.error, a.submission_started)
    print(json.dumps({'facebook': m['channels']['facebook'], 'submission_count': len(m['submission_history'])}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
