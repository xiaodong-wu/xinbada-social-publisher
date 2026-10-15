#!/usr/bin/env python3
"""Discover the complete Xinbada catalog and extract a bounded, auditable selection."""
from __future__ import annotations
import argparse
import io
import random
import re
import sys
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from uuid import uuid4
from PIL import Image, UnidentifiedImageError
from common import *

VOID = set('area base br col embed hr img input link meta param source track wbr'.split())


class Node:
    def __init__(self, tag='root', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def nodes(self, tag=None, cls=None):
        result = []
        for child in self.children:
            if isinstance(child, Node):
                if (tag is None or child.tag == tag) and (cls is None or cls in child.attrs.get('class', '').split()):
                    result.append(child)
                result.extend(child.nodes(tag, cls))
        return result

    def text(self):
        if self.tag in ('style', 'script', 'noscript'):
            return ''
        return clean(' '.join(c.text() if isinstance(c, Node) else c for c in self.children))


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


class SameSiteRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        site_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, limit=15 * 1024 * 1024):
    url = site_url(url)
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; XinbadaSocialPublisher/1.0)'})
    with build_opener(SameSiteRedirect()).open(req, timeout=35) as response:
        final = site_url(response.url)
        data = response.read(limit + 1)
        if len(data) > limit:
            raise RuntimeError('Source response exceeds size limit')
        return data, final


def listing(html, url):
    root = Document(html).root
    products, pages = set(), set()
    for card in root.nodes(cls='hn-card-title'):
        for a in card.nodes('a'):
            link = site_url(a.attrs.get('href', ''), url)
            if is_product(link):
                products.add(link)
    for pager in root.nodes(cls='hn-pagination'):
        for a in pager.nodes('a'):
            link = site_url(a.attrs.get('href', ''), url)
            if is_listing(link):
                pages.add(link)
    if not products:
        raise RuntimeError('Listing has no recognizable product cards; inspect template or access state')
    return sorted(products), sorted(pages)


def catalog(path):
    queue, visited, pool = deque([CATALOG]), set(), {}
    audit = {'source': CATALOG, 'created_at': now(), 'status': 'incomplete', 'pages': [], 'products': []}
    write(path, audit)
    try:
        while queue:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)
            try:
                data, final = fetch(url)
            except HTTPError as exc:
                if exc.code in (404, 410) and url != CATALOG:
                    audit['pages'].append({'url': url, 'status': 'missing', 'http_status': exc.code})
                    continue
                raise
            if not is_listing(final):
                raise RuntimeError('Listing redirected outside product catalog')
            products, pagination = listing(data.decode('utf-8'), final)
            audit['pages'].append({'url': url, 'final_url': final, 'status': 'ok', 'products': products, 'pagination': pagination})
            for product in products:
                pool.setdefault(product, []).append(url)
            queue.extend(p for p in pagination if p not in visited)
            audit['products'] = [{'url': u, 'listing_pages': p} for u, p in sorted(pool.items())]
            write(path, audit)
        audit.update(status='complete', product_count=len(pool), listing_count=len(audit['pages']))
        write(path, audit)
        return list(pool)
    except Exception as exc:
        audit.update(status='blocked', error=str(exc))
        write(path, audit)
        raise


ALIASES = {'main ingredient': 'ingredients', 'main ingredients': 'ingredients', 'formula': 'ingredients',
           'ingredients': 'ingredients', 'dosage form': 'format', 'format': 'format',
           'serving or dose': 'serving', 'serving': 'serving', 'dose': 'serving', 'listed dose': 'serving',
           'package': 'package', 'packaging': 'package', 'package specification': 'package',
           'shelf life': 'shelf_life',
           'flavor': 'flavor', 'flavour': 'flavor', 'private label': 'private_label'}


def first_text(root, cls):
    nodes = root.nodes(cls=cls)
    return nodes[0].text() if nodes else ''


def value_norm(value):
    # Cosmetic normalization only; decimals, units, ranges and qualifiers remain distinct.
    return re.sub(r'\s+', '', value.lower())


def formats(text):
    choices = {'powder': r'\bpowders?\b', 'capsule': r'\bcapsules?\b',
               'chew': r'\b(?:soft chews?|gumm(?:y|ies))\b', 'gel': r'\bgels?\b',
               'drops': r'\b(?:liquid drops?|oral liquid)\b', 'tablet': r'\btablets?\b'}
    return {key for key, pattern in choices.items() if re.search(pattern, text, re.I)}


def extract(html, url):
    root = Document(html).root
    # The rest of this site's detail page is a reused template, not product evidence.
    overviews = root.nodes('section', cls='product_overview')
    overview = overviews[0] if len(overviews) == 1 else Node()
    titles, summaries = overview.nodes(cls='ov_title'), overview.nodes(cls='ov_subtitle')
    title = titles[0].text() if len(titles) == 1 else ''
    summary = summaries[0].text() if len(summaries) == 1 else ''
    canon = [n.attrs.get('href', '') for n in root.nodes('link') if 'canonical' in n.attrs.get('rel', '').split()]
    canonical = site_url(canon[0], url) if canon else url
    if not is_product(canonical):
        raise ValueError('Canonical URL is not a product page')
    rows = []
    for group in overview.nodes(cls='ov_attributes'):
        for li in group.nodes('li'):
            key, sep, value = li.text().partition(':')
            if sep and value.strip() and norm(value) not in ('not stated', 'not specified', 'n a'):
                rows.append((key.strip(), value.strip(), 'overview'))
    records = {}
    for key, value, source in rows:
        key = ALIASES.get(norm(key), norm(key).replace(' ', '_'))
        records.setdefault(key, []).append({'value': value, 'source': source})
    declared, corroborated, conflicts = {}, {}, {}
    for key, items in records.items():
        distinct = {value_norm(item['value']) for item in items}
        if len(distinct) == 1:
            declared[key] = items[0]['value']
            if len({item['source'] for item in items}) > 1:
                corroborated[key] = items[0]['value']
        else:
            conflicts[key] = items
    gallery = []
    hero_groups = overview.nodes(cls='gallery_main')
    if len(hero_groups) == 1:
        images = hero_groups[0].nodes('img')
        if images:
            src = images[0].attrs.get('src') or images[0].attrs.get('data-src')
            if src:
                gallery.append(site_url(src, url))
    core_formats = formats(declared.get('format', ''))
    reasons = []
    if len(overviews) != 1:
        reasons.append('Expected exactly one current-product overview')
    if not title or not summary or len(declared) < 3:
        reasons.append('Insufficient product title, summary or structured facts')
    if conflicts:
        reasons.append('Conflicting structured product fields: ' + ', '.join(conflicts))
    if not gallery:
        reasons.append('No unambiguous same-site current-product hero')
    if core_formats and formats(title) and not core_formats.intersection(formats(title)):
        reasons.append('Title and overview physical formats conflict')
    return {'source_url': url, 'canonical_url': canonical, 'fetched_at': now(),
            'evidence_scope': EVIDENCE_SCOPE.copy(),
            'title': title, 'summary': summary, 'facts': {'declared': declared,
            'corroborated': corroborated, 'conflicts': conflicts, 'records': records},
            'gallery': gallery,
            'screening': {'status': 'rejected' if reasons else 'requires_editorial_review', 'reasons': reasons}}


class CandidateRejected(Exception):
    pass


def select(ledger_path):
    ledger = read(ledger_path)
    root = ledger_path.parent
    seen = {a.get('canonical_url', a['url']) for a in ledger['attempts']}
    for url in ledger['pool']:
        if url in {a['url'] for a in ledger['attempts']} or url in seen:
            continue
        if len(ledger['attempts']) >= 10:
            break
        directory = root / ('candidate-' + str(len(ledger['attempts']) + 1).zfill(2))
        (directory / 'source').mkdir(parents=True, exist_ok=False)
        (directory / 'evidence').mkdir()
        attempt = {'url': url, 'at': now(), 'directory': str(directory), 'status': 'reviewing'}
        ledger['attempts'].append(attempt)
        write(ledger_path, ledger)
        try:
            try:
                data, final = fetch(url)
            except HTTPError as exc:
                if exc.code in (404, 410):
                    raise CandidateRejected('Product source returned HTTP ' + str(exc.code)) from exc
                raise
            (directory / 'source/page.html').write_bytes(data)
            product = extract(data.decode('utf-8'), final)
            attempt['canonical_url'] = product['canonical_url']
            if product['canonical_url'] in seen:
                ledger.setdefault('aliases_skipped', []).append(attempt.copy())
                ledger['attempts'].pop()
                ledger['pool'] = [p for p in ledger['pool'] if p != url]
                # Retain source evidence; use a unique directory on the next selection.
                directory.rename(directory.with_name(directory.name + '-alias-' + uuid4().hex[:6]))
                write(ledger_path, ledger)
                continue
            seen.add(product['canonical_url'])
            write(directory / 'product.json', product)
            if product['screening']['reasons']:
                raise CandidateRejected('; '.join(product['screening']['reasons']))
            try:
                hero, _ = fetch(product['gallery'][0])
            except HTTPError as exc:
                if exc.code in (404, 410):
                    raise CandidateRejected('Hero missing') from exc
                raise
            try:
                with Image.open(io.BytesIO(hero)) as im:
                    im.verify()
                with Image.open(io.BytesIO(hero)) as im:
                    if min(im.size) < 400:
                        raise CandidateRejected('Hero is smaller than 400 pixels')
                    ext = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}.get(im.format)
                    if not ext:
                        raise CandidateRejected('Unsupported hero format')
            except (UnidentifiedImageError, OSError) as exc:
                raise CandidateRejected('Hero does not decode') from exc
            hero_path = 'source/hero' + ext
            (directory / hero_path).write_bytes(hero)
            manifest = {'schema_version': 1, 'skill': SKILL, 'created_at': now(), 'mode': ledger['mode'],
                        'target': {'page_id': PAGE_ID, 'url': FACEBOOK}, 'product_url': product['canonical_url'],
                        'selection_ledger': str(ledger_path), 'artifacts': {'product': 'product.json', 'hero': hero_path,
                        'copy': 'facebook.txt', 'keywords': 'keyword-plan.json', 'social': 'social.webp',
                        'upload': 'social-upload.jpg'}, 'channels': {'facebook': {'status': 'not_started'}},
                        'reporting': {'google_sheet': {'status': 'not_started'}},
                        'submission_history': [], 'history': []}
            manifest_path = directory / 'manifest.json'
            write(manifest_path, manifest)
            attempt.update(status='selected', manifest=str(manifest_path))
            ledger.update(status='selected', current_manifest=str(manifest_path))
            write(ledger_path, ledger)
            return {'status': 'requires_editorial_review', 'manifest': str(manifest_path),
                    'selection_ledger': str(ledger_path), 'candidates_tried': len(ledger['attempts'])}
        except CandidateRejected as exc:
            attempt.update(status='rejected', reason=str(exc))
            write(ledger_path, ledger)
        except Exception as exc:
            attempt.update(status='blocked', reason=str(exc))
            ledger.update(status='blocked', error=str(exc))
            write(ledger_path, ledger)
            raise
    ledger.update(status='blocked', error='Candidate budget or product pool exhausted', current_manifest=None)
    write(ledger_path, ledger)
    return {'status': 'blocked', 'selection_ledger': str(ledger_path), 'candidates_tried': len(ledger['attempts']), 'error': ledger['error']}


def retry(manifest_path, reason):
    m = load_manifest(manifest_path)
    ledger_path = Path(m['selection_ledger'])
    ledger = read(ledger_path)
    if ledger['current_manifest'] != str(manifest_path.resolve()):
        raise ValueError('Only the current candidate can be replaced')
    # Inspect every manifest in the invocation, not just mutable current status.
    for attempt in ledger['attempts']:
        if attempt.get('manifest'):
            previous = load_manifest(attempt['manifest'])
            if previous['submission_history'] or previous['channels']['facebook']['status'] in ('pending', 'uncertain', 'published'):
                raise ValueError('Cannot reselect after any submission')
    if m.get('candidate_status') == 'rejected':
        raise ValueError('Candidate already rejected')
    m['candidate_status'] = 'rejected'
    m['channels']['facebook'] = {'status': 'blocked', 'error': reason}
    write(manifest_path, m)
    ledger['attempts'][-1].update(status='rejected', reason=reason)
    ledger['current_manifest'] = None
    write(ledger_path, ledger)
    return select(ledger_path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-root', type=Path, default=Path.cwd() / 'campaign-runs')
    p.add_argument('--mode', choices=('live', 'dry-run'), default='live')
    p.add_argument('--product-url')
    p.add_argument('--catalog-only', action='store_true')
    p.add_argument('--retry-from', type=Path)
    p.add_argument('--reason')
    args = p.parse_args()
    if args.retry_from:
        if not args.reason or args.product_url or args.catalog_only:
            p.error('--retry-from requires --reason and cannot combine with product/catalog-only')
        result = retry(args.retry_from.resolve(), args.reason)
    else:
        root = args.output_root.resolve() / (now()[:19].replace(':', '').replace('-', '') + '-' + uuid4().hex[:8])
        root.mkdir(parents=True)
        if args.product_url:
            if args.catalog_only:
                p.error('--catalog-only cannot combine with --product-url')
            url = site_url(args.product_url)
            if not is_product(url):
                p.error('Expected a nutricdmo.com product detail URL')
            pool = [url]
        else:
            pool = catalog(root / 'catalog.json')
            random.SystemRandom().shuffle(pool)
        if args.catalog_only:
            result = {'status': 'catalog_complete', 'catalog': str(root / 'catalog.json'), 'products': len(pool)}
        else:
            ledger_path = root / 'selection-ledger.json'
            write(ledger_path, {'created_at': now(), 'mode': args.mode, 'targeted': bool(args.product_url),
                               'catalog': str(root / 'catalog.json') if not args.product_url else None,
                               'pool': pool, 'attempts': [], 'current_manifest': None, 'status': 'selecting'})
            result = select(ledger_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result['status'] == 'blocked' else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print('error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
