"""Offline behavioral regression checks. No network, imagegen or social side effects."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from common import *
from scrape_product import listing, catalog, extract, retry, select
from optimize_image import strip_metadata, create_transport_jpeg, encode_webp, validate as image_validate, main as optimize_main
from validate_campaign import validate
from update_manifest import update
from validate_completion import completion


def fixture(root, mode='live'):
    (root / 'source').mkdir()
    (root / 'evidence').mkdir()
    html = '''<section class="product_overview">
      <h1 class="ov_title">Xinbada Creatine Monohydrate Powder OEM ODM</h1>
      <p class="ov_subtitle">Unflavored powder for private label projects.</p>
      <ul class="ov_attributes"><li>Ingredients: Creatine monohydrate</li><li>Format: Powder</li>
      <li>Private label: Private label OEM ODM</li><li>Package: 500g jar</li></ul>
      <div class="gallery_main"><img src="/hero.png"></div></section>'''
    (root / 'source/page.html').write_text(html)
    product = extract(html, BASE + '/test-product.html')
    write(root / 'product.json', product)
    copy = '''🧪 Creatine monohydrate powder offers a focused starting point for your next sourcing discussion.
📦 A 500g jar provides a clear packaging reference for a private label brief.
🏷️ Private label projects can begin with a review of the listed product information.
🤝 OEM ODM discussions can help your team define the questions that matter for procurement.

For supplement brands and distributors, a practical supplier conversation starts with a clear product brief. Review the formula and packaging details, then outline the information your team needs before making a purchasing decision.

Contact Xinbada to discuss your project requirements and request further product information.
https://www.nutricdmo.com/test-product.html
#Xinbada #PrivateLabel #OEM #ODM #Creatine #Powder #Sourcing #Supplements
'''
    (root / 'facebook.txt').write_text(copy)
    write(root / 'keyword-plan.json', {'core_keyword': 'creatine monohydrate powder', 'related_keywords': ['private label', 'OEM ODM'], 'buyer_intent': 'sourcing', 'evidence': [
        {'keyword': 'creatine monohydrate powder', 'source_id': 'title', 'quote': product['title']},
        {'keyword': 'private label', 'source_id': 'summary', 'quote': product['summary']},
        {'keyword': 'OEM ODM', 'source_id': 'title', 'quote': product['title']}]})
    im = Image.new('RGB', (1024, 1024), '#e0ece2')
    im.save(root / 'source/hero.png')
    (root / 'social.webp').write_bytes(encode_webp(strip_metadata(im), 82))
    create_transport_jpeg(im, root / 'social-upload.jpg')
    Image.new('RGB', (800, 600), 'white').save(root / 'evidence/preview.png')
    write(root / 'evidence/content-review.json', {'verdict': 'pass', 'copy_sha256': sha(root/'facebook.txt'), 'product_sha256': sha(root/'product.json'),
        'source_and_hero_reviewed': True, 'no_unresolved_conflicts': True, 'no_health_or_certification_claims': True,
        'claims': [{'claim': '500g jar', 'source_id': 'facts.package', 'quote': '500g jar'},
                   {'claim': 'Creatine monohydrate powder', 'source_id': 'title', 'quote': product['title']},
                   {'claim': 'Private label', 'source_id': 'facts.private_label', 'quote': 'Private label OEM ODM'},
                   {'claim': 'OEM ODM', 'source_id': 'title', 'quote': product['title']}], 'notes': 'Synthetic offline fixture, not for publication.'})
    write(root / 'evidence/image-review.json', {'verdict': 'pass', 'attempts': 1, 'four_panels': True, 'identity_preserved': True,
        'source_sha256': sha(root/'source/hero.png'), 'social_sha256': sha(root/'social.webp'), 'upload_sha256': sha(root/'social-upload.jpg'), 'notes': 'Synthetic test fixture; visual assertions simulated.'})
    manifest = {'schema_version': 1, 'skill': SKILL, 'created_at': now(), 'mode': mode, 'target': {'page_id': PAGE_ID, 'url': FACEBOOK},
        'product_url': product['canonical_url'], 'selection_ledger': str(root/'selection-ledger.json'),
        'artifacts': {'product':'product.json','hero':'source/hero.png','copy':'facebook.txt','keywords':'keyword-plan.json','social':'social.webp','upload':'social-upload.jpg'},
        'channels':{'facebook':{'status':'not_started'}},'submission_history':[], 'history':[]}
    path=root/'manifest.json'; write(path,manifest)
    write(root/'selection-ledger.json', {'mode': mode,'pool':[product['canonical_url']], 'attempts':[{'url':product['canonical_url'],'status':'selected','manifest':str(path)}], 'current_manifest':str(path)})
    write(root/'evidence/preflight.json', {'checked_at':now(),'page_id':PAGE_ID,'page_url':FACEBOOK,'observed_page_name':'Synthetic test', 'active_identity_verified':True,'can_create_post':True,'preview_verified':True,'copy_sha256':sha(root/'facebook.txt'),'upload_sha256':sha(root/'social-upload.jpg'),'screenshot':'evidence/preview.png'})
    return path


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.path = fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_batch_and_dry_run(self):
        self.assertEqual(validate(self.path)['status'], 'valid')
        m=read(self.path); m['mode']='dry-run'; write(self.path,m)
        self.assertEqual(completion(self.path)['status'],'dry-run')
        with self.assertRaisesRegex(ValueError,'Dry-run'):
            update(self.path,'pending',submission_started=True)

    def test_identity_and_freshness_block(self):
        pre=read(self.root/'evidence/preflight.json'); pre['page_id']='61568292290322'
        write(self.root/'evidence/preflight.json',pre)
        with self.assertRaisesRegex(ValueError,'target mismatch'):
            update(self.path,'pending',submission_started=True)
        self.assertFalse(read(self.path)['submission_history'])
        pre['page_id']=PAGE_ID; pre['checked_at']='2000-01-01T00:00:00+00:00'
        write(self.root/'evidence/preflight.json',pre)
        with self.assertRaisesRegex(ValueError,'stale'):
            update(self.path,'pending',submission_started=True)

    def test_published_requires_submission_and_author(self):
        url='https://www.facebook.com/'+PAGE_ID+'/posts/123456'
        with self.assertRaisesRegex(ValueError,'No recorded submission'):
            update(self.path,'published',url=url)
        update(self.path,'pending',submission_started=True)
        ev={'checked_at':now(),'url':url,'page_id':PAGE_ID,'author_page_id':PAGE_ID,'copy_sha256':sha(self.root/'facebook.txt'), 'social_sha256':sha(self.root/'social.webp'), 'text_matches':True,'image_matches':True,'product_link_matches':True,'published_visible':True,'screenshot':'evidence/preview.png','verification_context':'Offline simulated verification'}
        ev['author_page_id']='999'
        write(self.root/'evidence/facebook-verification.json',ev)
        with self.assertRaisesRegex(ValueError,'author identity'):
            update(self.path,'published',url=url)
        ev['author_page_id']=PAGE_ID
        write(self.root/'evidence/facebook-verification.json',ev)
        update(self.path,'published',url=url)
        self.assertEqual(completion(self.path)['status'],'complete')
        (self.root/'social-upload.jpg').unlink()
        self.assertEqual(completion(self.path)['status'],'complete')
        with self.assertRaisesRegex(ValueError,'terminal'):
            update(self.path,'pending',submission_started=True)

    def test_uncertainty_preserves_history_and_bounds_retry(self):
        update(self.path,'pending',submission_started=True)
        update(self.path,'uncertain',error='simulated')
        with self.assertRaises(FileNotFoundError):
            update(self.path,'pending',submission_started=True)
        write(self.root/'evidence/reconciliation.json',{'checked_at':now(),'page_id':PAGE_ID,'verdict':'not_published','published_checked':True,'scheduled_checked':True,'drafts_checked':True,'notes':'Synthetic test','screenshot':'evidence/preview.png'})
        update(self.path,'pending',submission_started=True)
        update(self.path,'failed',error='simulated')
        with self.assertRaisesRegex(ValueError,'one retry'):
            update(self.path,'pending',submission_started=True)
        self.assertEqual(len(read(self.path)['submission_history']),2)
        with self.assertRaisesRegex(ValueError,'Cannot reselect'):
            retry(self.path,'new source issue')

    def test_changed_copy_cannot_retry_or_complete(self):
        update(self.path,'pending',submission_started=True)
        with (self.root/'facebook.txt').open('a') as file:
            file.write('extra text')
        with self.assertRaisesRegex(ValueError,'changed'):
            update(self.path,'pending',submission_started=True)
        with self.assertRaises(ValueError):
            completion(self.path)

    def test_stale_review_and_keyword_source(self):
        plan=read(self.root/'keyword-plan.json'); plan['evidence'][0]['quote']='unrelated source'
        write(self.root/'keyword-plan.json',plan)
        with self.assertRaisesRegex(ValueError,'exact source'):
            validate(self.path)

    def test_numeric_claim_cannot_use_wrong_source_value(self):
        copy_path=self.root/'facebook.txt'
        copy_path.write_text(copy_path.read_text().replace('500g jar','1000g jar'))
        review=read(self.root/'evidence/content-review.json')
        review['copy_sha256']=sha(copy_path)
        review['claims'][0]['claim']='1000g jar'
        write(self.root/'evidence/content-review.json',review)
        with self.assertRaisesRegex(ValueError,'Numeric claim differs'):
            validate(self.path)

    def test_old_or_polluted_extraction_cannot_publish(self):
        product = read(self.root/'product.json')
        product.pop('evidence_scope')
        write(self.root/'product.json', product)
        with self.assertRaisesRegex(ValueError, 'evidence scope is outdated'):
            validate(self.path)
        product['evidence_scope'] = EVIDENCE_SCOPE.copy()
        product['facts']['declared']['ingredients'] = 'Unrelated template formula'
        write(self.root/'product.json', product)
        with self.assertRaisesRegex(ValueError, 'differs from scoped source extraction'):
            validate(self.path)

    def test_wrong_permalink_and_image_size(self):
        self.assertFalse(permalink(FACEBOOK))
        self.assertFalse(permalink('https://www.facebook.com/999/posts/123'))
        self.assertFalse(permalink('https://www.facebook.com.evil.test/'+PAGE_ID+'/posts/123'))
        self.assertTrue(permalink('https://www.facebook.com/permalink.php?story_fbid=pfbidABC&id='+PAGE_ID))
        Image.new('RGB',(200,200)).save(self.root/'small.webp')
        with self.assertRaisesRegex(RuntimeError,'960'):
            image_validate(self.root/'small.webp','social',750*1024)

    def test_no_upscale_and_metadata_strip(self):
        small=self.root/'small.png'; Image.new('RGB',(300,300)).save(small)
        with patch('sys.argv',['optimize_image.py',str(small),str(self.root/'out.webp'),'--kind','social']):
            with self.assertRaisesRegex(ValueError,'below 960'):
                optimize_main()
        im=Image.new('RGB',(1024,1024)); im.info['icc_profile']=b'fake profile'
        self.assertFalse(strip_metadata(im).info)


class ExtractionTests(unittest.TestCase):
    OVERVIEW = '<section class="product_overview"><h1 class="ov_title">Creatine Soft Chews</h1><p class="ov_subtitle">Private label supply</p><ul class="ov_attributes"><li>Dosage Form: Soft chews</li><li>Package: 60 chews</li><li>Shelf Life: 18 months</li></ul><div class="gallery_main"><img src="/hero.webp"><img src="/other.webp"></div></section>'
    def test_pagination_traversal_dedup_and_later_links(self):
        def page(product, links):
            return '<h3 class="hn-card-title"><a href="/'+product+'.html">P</a></h3><div class="hn-pagination">'+''.join('<a href="'+x+'">Next</a>' for x in links)+'</div>'
        pages={CATALOG:page('a',['/product/index.html','/product/2.html']), BASE+'/product/2.html':page('b',['/product/3.html']), BASE+'/product/3.html':page('c',['/product/2.html'])}
        with tempfile.TemporaryDirectory() as temp, patch('scrape_product.fetch',side_effect=lambda u:(pages[u].encode(),u)):
            path=Path(temp)/'catalog.json'
            self.assertEqual(set(catalog(path)),{BASE+'/'+x+'.html' for x in 'abc'})
            self.assertEqual(read(path)['listing_count'],3)

    def test_generic_template_is_neither_evidence_nor_rejection(self):
        template = '<article class="pd_formula_item"><h3>Package</h3><p>120 chews</p></article><article class="pd_story_tile">Oral Liquid Drops B12</article><div class="ov_title">Wrong footer title</div><div class="ov_subtitle">Wrong footer summary</div><ul class="ov_attributes"><li>Package: 60mL drops</li></ul><div class="gallery_main"><img src="/footer.webp"></div>'
        product=extract(template+self.OVERVIEW+template,BASE+'/a.html')
        self.assertEqual(source_map(product),{'title':'Creatine Soft Chews','summary':'Private label supply','facts.format':'Soft chews','facts.package':'60 chews','facts.shelf_life':'18 months'})
        self.assertEqual(product['gallery'], [BASE+'/hero.webp'])
        self.assertNotIn('review_only', product)
        self.assertFalse(product['screening']['reasons'])

    def test_current_product_conflict_still_rejected(self):
        html=self.OVERVIEW.replace('</ul>', '<li>Package specification: 120 chews</li></ul>').replace('Creatine Soft Chews','Creatine Powder')
        product=extract(html,BASE+'/a.html')
        self.assertIn('package',product['facts']['conflicts'])
        self.assertEqual(product['screening']['status'],'rejected')
        self.assertEqual(len(product['screening']['reasons']),3)

    def test_missing_or_ambiguous_overview_never_falls_back(self):
        for html in (self.OVERVIEW.replace('product_overview','generic_template'), self.OVERVIEW*2):
            product=extract(html, BASE+'/a.html')
            self.assertEqual(source_map(product), {'title':'','summary':''})
            self.assertEqual(product['gallery'], [])
            self.assertEqual(product['screening']['status'],'rejected')

    def test_missing_hero_and_unspecified_facts_never_fall_back(self):
        html=self.OVERVIEW.replace('gallery_main','thumbnails').replace('60 chews','Not stated')
        html += '<div class="gallery_main"><img src="/template.webp"></div>'
        product=extract(html, BASE+'/a.html')
        self.assertNotIn('package', product['facts']['declared'])
        self.assertFalse(product['gallery'])
        self.assertEqual(product['screening']['status'],'rejected')

    def test_complete_pool_budget_and_targeted_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); ledger=root/'selection-ledger.json'
            pool=[BASE+'/'+str(n)+'.html' for n in range(12)]
            write(ledger,{'mode':'dry-run','pool':pool,'attempts':[],'current_manifest':None})
            with patch('scrape_product.fetch',return_value=(b'<html></html>',pool[0])):
                # Distinct canonical URLs for this test; no alias shortcut.
                with patch('scrape_product.extract',side_effect=lambda html,url: {'canonical_url':pool[len(read(ledger)['attempts'])-1], 'screening':{'reasons':['insufficient']}}):
                    self.assertEqual(select(ledger)['candidates_tried'],10)
            self.assertEqual(read(ledger)['status'],'blocked')

    def test_targeted_candidate_is_not_substituted(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger=Path(temp)/'selection-ledger.json'
            write(ledger,{'mode':'dry-run','targeted':True,'pool':[BASE+'/single.html'],'attempts':[],'current_manifest':None})
            with patch('scrape_product.fetch',return_value=(b'<html></html>',BASE+'/single.html')):
                result=select(ledger)
            self.assertEqual(result['status'],'blocked')
            self.assertEqual(result['candidates_tried'],1)


if __name__=='__main__':
    unittest.main(verbosity=2)
