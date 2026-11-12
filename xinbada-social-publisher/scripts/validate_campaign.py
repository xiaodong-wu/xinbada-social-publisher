#!/usr/bin/env python3
"""Validate local Facebook campaign content, evidence linkage and image files."""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
from PIL import Image
from common import *
from optimize_image import validate as validate_webp
from scrape_product import extract

# These are screening signals, not a complete semantic health-claim classifier.
RISKY = re.compile(r'\b(?:cures?|treats?|prevents?|clinically proven|FDA[- ]approved|guaranteed|'
                   r'weight loss|burns? fat|boosts? immunity|muscle growth|GMP[- ]certified|'
                   r'HALAL[- ]certified|organic[- ]certified)\b', re.I)
NUMBERS = re.compile(r'\d+(?:\.\d+)?')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_evidence(item, sources):
    require(item.get('source_id') in sources, 'Unknown claim/keyword source_id')
    quote = item.get('quote', '')
    require(bool(quote) and quote in sources[item['source_id']], 'Evidence quote must be an exact source excerpt')


def validate(manifest_path, include_upload=True):
    manifest_path = Path(manifest_path).resolve()
    root = manifest_path.parent
    m = load_manifest(manifest_path)
    require(m.get('candidate_status') != 'rejected', 'Candidate was rejected')
    paths = {key: within(root, relative) for key, relative in m['artifacts'].items()}
    require(set(paths) == {'product', 'hero', 'copy', 'keywords', 'social', 'upload'}, 'Artifact set mismatch')
    product = read(paths['product'])
    require(product['canonical_url'] == m['product_url'], 'Product URL mismatch')
    require(not product['facts']['conflicts'] and not product['screening']['reasons'], 'Unresolved source conflicts')
    sources = source_map(product)
    extracted = extract((root / 'source/page.html').read_text(encoding='utf-8'), product['source_url'])
    for key in ('canonical_url', 'title', 'summary', 'facts', 'gallery', 'evidence_scope', 'screening'):
        require(product.get(key) == extracted.get(key), 'Product differs from scoped source extraction: ' + key)
    with Image.open(paths['hero']) as hero:
        hero.verify()
    copy = paths['copy'].read_text(encoding='utf-8').strip()
    lines = [line.strip() for line in copy.splitlines() if line.strip()]
    legacy = legacy_product_link(m, paths['copy'])
    require(len(lines) >= (8 if legacy else 7), 'Expected four features, paragraph, CTA and hashtag line')
    require(all(re.match(r'^[\U0001F000-\U0001FAFF\u2600-\u27BF]', line) for line in lines[:4]), 'First four lines must be emoji-led features')
    if legacy:
        require(lines[-2] == m['product_url'], 'Legacy canonical URL must be on the penultimate nonempty line')
        require(re.findall(r'https?://\S+', copy) == [m['product_url']], 'Legacy copy must retain its original product URL')
    else:
        require(not WEBSITE_LINK.search(copy), 'Social copy must not contain website links or bare domains')
    hashtags = re.findall(r'#[A-Za-z][A-Za-z0-9_]*', lines[-1])
    require(8 <= len(hashtags) <= 12 and len(set(h.lower() for h in hashtags)) == len(hashtags), 'Use 8-12 distinct hashtags')
    require(' '.join(hashtags) == clean(lines[-1]), 'Last line must contain hashtags only')
    body = '\n'.join(lines[:-2] if legacy else lines[:-1])
    require(not re.search(r'[\u4e00-\u9fff]|<[^>]+>', body), 'Post must be English plain text')
    words = re.findall(r"\b[A-Za-z]+(?:[-'][A-Za-z]+)*\b", body)
    require(80 <= len(words) <= 150, 'Body word count must be 80-150; got ' + str(len(words)))
    require(not RISKY.search(body), 'Potential unsupported health/certification/guarantee wording')
    plan = read(paths['keywords'])
    keywords = [plan['core_keyword']] + plan['related_keywords']
    require(2 <= len(plan['related_keywords']) <= 4 and 2 <= len(norm(plan['core_keyword']).split()) <= 8, 'Keyword count/length invalid')
    require(len(set(norm(k) for k in keywords)) == len(keywords), 'Duplicate keywords')
    require(bool(plan.get('buyer_intent')), 'Buyer intent missing')
    require(norm(plan['core_keyword']) in norm(body), 'Core keyword missing from post')
    evidence = plan['evidence']
    require(len(evidence) == len(keywords) and {e['keyword'] for e in evidence} == set(keywords), 'Keyword evidence incomplete')
    for item in evidence:
        check_evidence(item, sources)
        require(norm(item['keyword']) in norm(item['quote']), 'Keyword not grounded in quoted source')
        require(not RISKY.search(item['keyword']), 'Risky claim in keyword')
    review_path = root / 'evidence/content-review.json'
    review = read(review_path)
    require(review.get('verdict') == 'pass', 'Content review has not passed')
    for key in ('source_and_hero_reviewed', 'no_unresolved_conflicts', 'no_health_or_certification_claims'):
        require(review.get(key) is True, 'Content review missing: ' + key)
    require(review['copy_sha256'] == sha(paths['copy']) and review['product_sha256'] == sha(paths['product']), 'Content review hashes are stale')
    require(bool(review.get('notes')) and bool(review.get('claims')), 'Content review notes/claims missing')
    covered = []
    for item in review['claims']:
        check_evidence(item, sources)
        require(bool(item.get('claim')) and item['claim'] in body, 'Mapped claim is missing from post')
        require(set(NUMBERS.findall(item['claim'])) <= set(NUMBERS.findall(item['quote'])), 'Numeric claim differs from its source quote')
        covered.append(item['claim'])
    for number in NUMBERS.findall(body):
        require(any(number in claim for claim in covered), 'Numeric claim lacks explicit source mapping: ' + number)
    webp = validate_webp(paths['social'], 'social', 750 * 1024)
    if include_upload:
        require(paths['upload'].stat().st_size <= 750 * 1024, 'JPEG exceeds 750 KiB')
        with Image.open(paths['upload']) as im:
            im.verify()
        with Image.open(paths['upload']) as im:
            require(im.format == 'JPEG' and im.size == (webp['width'], webp['height']), 'JPEG format/dimensions mismatch')
            require(not im.getexif() and not any(k in im.info for k in ('exif', 'xmp', 'icc_profile', 'comment')), 'JPEG contains metadata')
    image_review_path = root / 'evidence/image-review.json'
    image_review = read(image_review_path)
    require(image_review.get('verdict') == 'pass' and image_review.get('four_panels') is True and image_review.get('identity_preserved') is True, 'Visual review incomplete')
    require(1 <= image_review.get('attempts', 0) <= 4 and bool(image_review.get('notes')), 'Image recovery history invalid')
    require(image_review['source_sha256'] == sha(paths['hero']) and image_review['social_sha256'] == sha(paths['social']), 'Visual review hashes are stale')
    if include_upload:
        require(image_review['upload_sha256'] == sha(paths['upload']), 'JPEG visual review is stale')
    hashes = {key: sha(path) for key, path in paths.items() if key != 'upload' or include_upload}
    hashes['content_review'] = sha(review_path)
    hashes['image_review'] = sha(image_review_path)
    return {'status': 'valid', 'checked_at': now(), 'copy_policy': 'legacy_product_link' if legacy else NO_WEBSITE_LINKS,
            'word_count': len(words), 'hashtag_count': len(hashtags), 'image': webp, 'hashes': hashes}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path)
    args = p.parse_args()
    evidence = args.manifest.resolve().parent / 'evidence/campaign-validation.json'
    try:
        result = validate(args.manifest)
    except Exception as exc:
        write(evidence, {'status': 'failed', 'checked_at': now(), 'error': str(exc)})
        raise
    write(evidence, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
