# Product selection

Traverse all linked pagination under `https://www.nutricdmo.com/product/`. `/product/`,
`/product/index.html` and `/product/1.html` are first-page aliases. Read product cards, not all site
links. Save `catalog.json` with listings, product links, pagination, missing 404/410 pages and
coverage status. Non-missing unreadable listings block complete discovery. Later-page links join
the queue until it is empty; no page-count cap and no sampling only the first page.

Shuffle the full deduplicated pool once and save `selection-ledger.json`. Try up to ten distinct
candidates including manual rejections. Extract `ov_title`, `ov_subtitle`, `ov_attributes`,
`pd_formula_item`, gallery hero and product body. Save raw HTML. The scraper detects conflicting
structured values conservatively; it cannot decide all unfamiliar wording is equivalent.

Some observed pages contain unrelated template content. Generic company/FAQ content is excluded
as evidence, but product-specific `pd_story_tile` and headings must still be checked for mismatched
formula/format/package. Such conflicts reject the candidate, not justify choosing a convenient
version. Automated screening covers structured conflicts and obvious incompatible formats, and
requires the agent to review everything else before generating.

Missing or undecodable hero, insufficient facts, conflicting formula/quantity/format, mixed-product
sections or missing keyword evidence reject a candidate. Tool/disk/network/authentication/catalog
failures stop the invocation. Candidate HTTP 404/410 is a source rejection; 403/429/timeouts cannot
be evaded through reselection.

Use `--retry-from MANIFEST --reason TEXT` to reject a selected candidate before submission. It marks
the old candidate rejected and preserves the same ledger and budget. A targeted `--product-url`
cannot be substituted. Never recycle rejected copy/images. If exhausted, report the blocked ledger
even if no publishable manifest exists. Fresh invocations get fresh ledgers; resumption requires
user direction. Canonical aliases already reviewed are skipped without using another review slot.
