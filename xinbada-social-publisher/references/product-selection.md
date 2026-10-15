# Product selection

Traverse all linked pagination under `https://www.nutricdmo.com/product/`. `/product/`,
`/product/index.html` and `/product/1.html` are first-page aliases. Read product cards, not all site
links. Save `catalog.json` with listings, product links, pagination, missing 404/410 pages and
coverage status. Non-missing unreadable listings block complete discovery. Later-page links join
the queue until it is empty; no page-count cap and no sampling only the first page.

Shuffle the full deduplicated pool once and save `selection-ledger.json`. Try up to ten distinct
candidates including manual rejections. Inside exactly one `section.product_overview`, extract
only its unique `ov_title`, unique `ov_subtitle`, `ov_attributes li` specifications and first
`gallery_main img` as the hero. A missing/ambiguous overview must not fall back to global selectors.
Only this hero is a visual reference; secondary gallery and template images are excluded.
Save full raw HTML for audit, not as additional content evidence. Product JSON records evidence
scope version 2 and only these fields; unspecified values are omitted from declared facts.

The site's lower detail modules repeat generic content about other products. Exclude all
`product_detail_box`, `pd_formula_item`, `pd_story_tile`, company, FAQ, recommendation and footer
content, including their headings, quantities, formulas and images. Do not use them in keywords,
copy or image prompts, and do not reject a candidate because they conflict with the allowed fields.
Review only the current product's title, summary, overview specifications and hero for consistency.
Conflicts within that allowed evidence still reject the candidate. Missing facts remain missing.
The campaign validator re-extracts archived HTML and compares the allowed fields; old broad-scope
extractions cannot publish. Start a fresh extraction instead of modifying historical run records.

Missing or undecodable hero, insufficient allowed facts, conflicting formula/quantity/format
within the allowed evidence or missing keyword evidence reject a candidate. Tool/disk/network/authentication/catalog
failures stop the invocation. Candidate HTTP 404/410 is a source rejection; 403/429/timeouts cannot
be evaded through reselection.

Use `--retry-from MANIFEST --reason TEXT` to reject a selected candidate before submission. It marks
the old candidate rejected and preserves the same ledger and budget. A targeted `--product-url`
cannot be substituted. Never recycle rejected copy/images. If exhausted, report the blocked ledger
even if no publishable manifest exists. Fresh invocations get fresh ledgers; resumption requires
user direction. Canonical aliases already reviewed are skipped without using another review slot.
