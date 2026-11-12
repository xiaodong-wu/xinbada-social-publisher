"""Shared constants and local evidence helpers; no publishing operations."""
from __future__ import annotations
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qs
from uuid import uuid4

BASE = 'https://www.nutricdmo.com'
CATALOG = BASE + '/product/'
PAGE_ID = '61589310638473'
FACEBOOK = 'https://www.facebook.com/profile.php?id=' + PAGE_ID
SKILL = 'xinbada-social-publisher'
NO_WEBSITE_LINKS = 'no_website_links'
WEBSITE_LINK = re.compile(
    r'\b(?:[a-z][a-z0-9+.-]*://|www\.)|'
    r'(?<![\w@])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]+)\b', re.I)
EVIDENCE_SCOPE = {
    'version': 2,
    'container': 'section.product_overview',
    'title': '.ov_title',
    'summary': '.ov_subtitle',
    'specifications': '.ov_attributes li',
    'hero': '.gallery_main img:first',
}


def now():
    return datetime.now(timezone.utc).isoformat()


def clean(text):
    return re.sub(r'\s+', ' ', text).strip()


def norm(text):
    return clean(re.sub(r'[^a-z0-9]+', ' ', text.lower()))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def legacy_product_link(m, copy_path):
    """Keep only pre-policy submitted copy compatible; fresh drafts never qualify."""
    history = m.get('submission_history', [])
    return bool(history and 'copy_policy' not in history[0]
                and history[0].get('hashes', {}).get('copy') == sha(copy_path)
                and m['product_url'] in Path(copy_path).read_text(encoding='utf-8').splitlines())


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def site_url(url, base=BASE):
    p = urlsplit(urljoin(base, url.strip()))
    if p.scheme not in ('http', 'https') or p.hostname not in ('nutricdmo.com', 'www.nutricdmo.com') or p.username or p.password or p.port not in (None, 80, 443):
        raise ValueError('URL must belong to nutricdmo.com')
    path = p.path or '/'
    if path in ('/product', '/product/index.html', '/product/1.html'):
        path = '/product/'
    # Tracking queries do not define a distinct product on the observed site.
    return urlunsplit(('https', 'www.nutricdmo.com', path, '', ''))


def is_listing(url):
    return bool(re.fullmatch(r'/product/(?:[2-9]\d*\.html|1\d+\.html)?', urlsplit(url).path))


def is_product(url):
    return bool(re.fullmatch(r'/[^/]+\.html', urlsplit(url).path))


def within(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Artifact path escapes run directory')
    return path


def load_manifest(path):
    path = Path(path).resolve()
    m = read(path)
    if m.get('skill') != SKILL or m.get('schema_version') != 1 or m.get('target') != {'page_id': PAGE_ID, 'url': FACEBOOK}:
        raise ValueError('Manifest skill/schema/Facebook target mismatch')
    if m.get('mode') not in ('live', 'dry-run') or set(m.get('channels', {})) != {'facebook'}:
        raise ValueError('Invalid mode or unsupported publishing channels')
    if site_url(m['product_url']) != m['product_url'] or not is_product(m['product_url']):
        raise ValueError('Invalid canonical product URL')
    for relative in m['artifacts'].values():
        within(path.parent, relative)
    return m


def source_map(product):
    if product.get('evidence_scope') != EVIDENCE_SCOPE:
        raise ValueError('Product evidence scope is outdated; start a fresh extraction')
    return {'title': product['title'], 'summary': product['summary'],
            **{'facts.' + key: value for key, value in product['facts']['declared'].items()}}


def permalink(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in ('www.facebook.com', 'facebook.com', 'm.facebook.com') or p.username or p.password or p.port not in (None, 443):
        return False
    q = parse_qs(p.query)
    if p.path in ('/permalink.php', '/story.php'):
        return q.get('id') == [PAGE_ID] and len(q.get('story_fbid', [])) == 1 and bool(re.fullmatch(r'[A-Za-z0-9]+', q['story_fbid'][0]))
    match = re.fullmatch(r'/([A-Za-z0-9.]+)/posts/([A-Za-z0-9]+)/?', p.path)
    return bool(match and (not match[1].isdigit() or match[1] == PAGE_ID))


def fresh(timestamp, seconds=900):
    value = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('Timestamp requires timezone')
    elapsed = (datetime.now(timezone.utc) - value).total_seconds()
    return -30 <= elapsed <= seconds


def screenshot(root, relative):
    from PIL import Image
    path = within(root, relative)
    with Image.open(path) as im:
        im.verify()
    return path
