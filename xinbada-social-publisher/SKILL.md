---
name: xinbada-social-publisher
description: 为辛巴达 Xinbada 从 nutricdmo.com/product/ 随机或指定选取营养补充剂产品，生成英文 B2B Facebook 文案和四宫格配图，发布到主页 61589310638473，按 Facebook 链接去重写入 Google Sheets 并返回中文发布清单。用于辛巴达 Facebook 产品推广、自动发布、登记补写或 dry-run；不包含站内文章和 LinkedIn 发布。
---

# 辛巴达社媒自动发布

One invocation produces at most one Xinbada Facebook product post. Destination:
`https://www.facebook.com/profile.php?id=61589310638473`. Source catalog:
`https://www.nutricdmo.com/product/`.

An explicit request to run this skill (including an authorized scheduled trigger) authorizes
publishing and the mandatory Google Sheets audit row after preflight and validation without another routine confirmation. Creating, editing
or inspecting the skill does not authorize a live run. `dry-run` creates local assets only.
Automatic discovery alone is not publishing authorization. Create a schedule only when requested.

## Workflow

1. **Preflight.** Read [publishing.md](references/publishing.md). Discover publishing connectors
   first; otherwise use the supported authenticated Chrome tool and its current documentation.
   Confirm exact page ID, active posting identity and create-post permission. Allow the bounded
   target-page switch in the reference. Stop for login, MFA, CAPTCHA, ambiguous identity or missing
   permission before generating. Dry-run requires no Facebook login. Confirm Python 3.10+ and
   Pillow (`python3 -c 'from PIL import Image'`). No website API or API key is needed.
2. **Select and review.** Read [product-selection.md](references/product-selection.md). Run
   `scripts/scrape_product.py --output-root RUNS_ROOT --mode live|dry-run`. Default `RUNS_ROOT` is
   `campaign-runs` in the current workspace. Use `--product-url URL` when supplied. Inspect the
   live page, `source/page.html`, `product.json` and `source/hero.*`. Discover all listing pages
   before shuffling; retain the shared ten-candidate limit. Use only the unique top
   `section.product_overview`: title, summary, overview specifications and first main image.
   Ignore all generic detail templates, including `pd_formula_item`, `pd_story_tile`, FAQs,
   recommendations and their other-product text/images; these are neither facts nor rejection
   reasons. Reject contradictions within the allowed fields or between those fields and the hero.
   Scripts do not replace editorial review. Never fill missing facts from the excluded templates.
   Use `--retry-from MANIFEST --reason TEXT` for a source rejection before any submission.
   A targeted product cannot be substituted. Store artifacts outside the installed skill.
3. **Draft.** Read [content-spec.md](references/content-spec.md). Generate `keyword-plan.json`
   from product evidence without asking for keywords. Save `facebook.txt`: 80–150 English words,
   four emoji-led feature lines, a buyer-oriented paragraph, an inquiry CTA and 8–12 relevant
   hashtags. Do not include website URLs or bare domains in the social copy. Keep the canonical
   product URL in source records, the manifest and the local report. Focus on supplement brands,
   distributors and private-label/OEM/ODM procurement. Avoid health outcomes, dosing advice and unsupported
   certifications. Save claim mappings in `evidence/content-review.json` as specified.
4. **Image.** Load the installed `imagegen` skill. Inspect the hero with `view_image`, then use it
   as the imagegen reference for one square four-panel image. Preserve the exact product, packaging
   and readable label identity. Use neutral product views when a scene is unverified. Generate no
   news cover or article images. Follow the bounded recovery in `content-spec.md`, copy accepted
   output into the run, and optimize:

   ```bash
   python3 scripts/optimize_image.py RUN/generated-social.png RUN/social.webp --kind social --transport-jpeg RUN/social-upload.jpg
   ```

   Both images must be square, 960–1600 pixels per side, metadata-free and at most 750 KiB.
   Inspect the optimized files and save `evidence/image-review.json` with their hashes.
5. **Validate.** Run `scripts/validate_campaign.py MANIFEST`. Fix draft/image errors on the same
   product; do not reselect to evade a broken tool. For dry-run, produce the local Chinese report
   and state nothing was published. For live mode, refresh identity and preview checks and save
   `evidence/preflight.json` following `publishing.md`.
6. **Publish and verify.** Upload only `social-upload.jpg` to the exact Facebook page. Immediately
   before final submit run `scripts/update_manifest.py MANIFEST --status pending
   --submission-started`, then click Publish once. Open the actual public permalink, verify author,
   copy, image and absence of website links/link previews, and save
   `evidence/facebook-verification.json` plus screenshot.
   Record `--status published --url PERMALINK`, then perform Sheets reporting below. Helpers
   validate records; they do not operate Facebook or independently prove remote state.
7. **Write Google Sheets.** Read [reporting.md](references/reporting.md) and follow the installed
   `google-drive:google-sheets` skill. Immediately after a verified Facebook publication, write one
   row to the fixed `social-auto-upload` spreadsheet. Use `nutricdmo.com`, the original publication
   verification time in Asia/Shanghai, an empty website cell, the verified Facebook permalink,
   and an empty LinkedIn cell. Deduplicate by Facebook link before writing. Read back the row and
   prove exactly one matching record, save raw connector evidence, then record reporting with
   `scripts/report_sheet.py MANIFEST --record reported`. Run `scripts/validate_completion.py MANIFEST`;
   only its `complete` result permits a completed live report. A Sheets failure leaves Facebook
   published and the overall workflow incomplete. Dry-run never writes Sheets.
8. **Report.** Save `report.md` and return a compact Chinese checklist: product/source URL,
   Facebook status/permalink, tried/skipped candidates with reasons, artifact directory, selection
   ledger, Google Sheets status/row/link and validation evidence. Distinguish
   blocked/failed/uncertain/dry-run/complete. Retain the JPEG for resumption; it may be removed
   after completion. Reporting-only repairs use the existing verified manifest and start at
   step 7; never select another product, regenerate content or republish Facebook for a Sheets repair.

## Failure and resume

- Product-source failures alone permit reselection, under the same ten-candidate budget including
  manual rejections. Environment/authentication failures stop the invocation.
- After submission begins, freeze product and content; preserve permanent submission history even
  when outcome is uncertain. Never erase the marker or replace the product.
- Reconcile ambiguity against published/scheduled/draft content before retrying. One retry at most,
  with evidence of non-publication; never submit twice speculatively or roll back success.
- Resume only when the user identifies a run or asks to resume the latest incomplete run / retry
  the just-reported blocker. Recheck identity and existing posts when Facebook verification is needed.
  Skip the Facebook publication step for already published runs; finish only missing reporting. A normal new
  invocation starts fresh and may repeat previous products.
- A dry-run manifest cannot become live by editing status; start a fresh authorized live run.

## Commands

Paths are relative to this skill. Helpers require the standard library plus Pillow.

```bash
python3 scripts/scrape_product.py [--output-root DIR] [--mode live|dry-run] [--product-url URL]
python3 scripts/scrape_product.py --retry-from MANIFEST --reason "Source conflict"
python3 scripts/scrape_product.py --catalog-only --output-root DIR
python3 scripts/optimize_image.py INPUT OUTPUT --kind social [--transport-jpeg PATH]
python3 scripts/validate_campaign.py MANIFEST
python3 scripts/update_manifest.py MANIFEST --status pending --submission-started
python3 scripts/update_manifest.py MANIFEST --status published --url URL
python3 scripts/update_manifest.py MANIFEST --status blocked --error TEXT
python3 scripts/report_sheet.py MANIFEST
python3 scripts/report_sheet.py MANIFEST --record reported
python3 scripts/report_sheet.py MANIFEST --record blocked --error TEXT
python3 scripts/validate_completion.py MANIFEST
```
