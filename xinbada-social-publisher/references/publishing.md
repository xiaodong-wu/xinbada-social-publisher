# Facebook publishing

Only destination: `https://www.facebook.com/profile.php?id=61589310638473`.
Confirm its visible name live; never substitute another brand's remembered session. Discover
connectors first, otherwise use current supported browser control of authenticated Chrome and read
its returned documentation. `cua_repl` can be a direct tool. Do not import legacy runtimes, access
credentials or bypass login. Missing identity/upload/preview/submit/verification capability blocks.

## One identity-switch sequence

Open the exact page in an authenticated session. If its panel explicitly offers to switch to that
same page, click once. If a confirmation dialog clearly identifies the same destination, confirm
once. Reopen the target URL; verify page ID, active posting identity and enabled create-post action.
No second switch, ambiguous account chooser, password, MFA or CAPTCHA handling. Stop if unresolved.

## Preview, submit and verify

Paste exact `facebook.txt`, upload `social-upload.jpg`, verify complete text, image, author and
absence of website links/link previews. Save screenshot evidence and `evidence/preflight.json`
immediately before final submit:

```json
{
  "checked_at": "ISO8601 WITH TIMEZONE",
  "page_id": "61589310638473",
  "page_url": "https://www.facebook.com/profile.php?id=61589310638473",
  "observed_page_name": "ACTUAL VISIBLE NAME",
  "active_identity_verified": true,
  "can_create_post": true,
  "preview_verified": true,
  "copy_sha256": "CURRENT facebook.txt HASH",
  "upload_sha256": "CURRENT social-upload.jpg HASH",
  "screenshot": "evidence/facebook-preview.png"
}
```

Run `update_manifest.py MANIFEST --status pending --submission-started`. Only after exit 0 click
Publish once. An enabled button or success toast alone is insufficient proof.

Find the post in target timeline/published content and open its actual public permalink. Verify
page-ID author, text, image and absence of website links/link previews. Never fabricate IDs.
A profile/admin/composer URL or opaque share shortcut is not a permalink. Accepted shapes include
`permalink.php?story_fbid=...&id=61589310638473` and `/<page-id-or-username>/posts/<post-id>`.
Username URLs require the recorded page-ID author check. Describe authenticated verification
accurately; do not claim anonymous accessibility when that was not tested.

Save `evidence/facebook-verification.json` with `checked_at`, `url`, `page_id`, `author_page_id`,
`copy_sha256`, `social_sha256`, `text_matches: true`, `image_matches: true`,
`no_website_links: true`, `published_visible: true`, `screenshot` (relative local path), and
`verification_context` describing observed UI/session. Run `update_manifest.py MANIFEST
--status published --url URL`, then `validate_completion.py MANIFEST`. The guards validate recorded
evidence and hashes, not remote state independently.

New submission history records `copy_policy: "no_website_links"`. Already-submitted batches
from before this rule keep their frozen copy, hashes, original verification time and existing
`product_link_matches` evidence. For those legacy batches only, verify the original product link
when reconciling or finishing reporting; do not edit or repost them to adopt the new copy rule.

## Ambiguity and retry

Record uncertain outcome using `--status uncertain --error TEXT`. Check target published,
scheduled and draft lists in the correct date range, matching product identity, exact copy and
image. If found, verify and record the existing post; if still unclear, stop without another click.

One retry is allowed only after evidence establishes non-publication. Save
`evidence/reconciliation.json` with `checked_at`, `page_id`, `verdict: "not_published"`,
`published_checked: true`, `scheduled_checked: true`, `drafts_checked: true`, `notes` and
`screenshot`. Preserve the product/copy/image, refresh preflight, then write another submission
marker. The second ambiguous/failed attempt stops. Published is terminal; no reporting failure
can authorize another post.
