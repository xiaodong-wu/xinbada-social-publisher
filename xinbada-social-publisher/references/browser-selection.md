# Find the Chrome extension and Xinbada tab

Apply this procedure to Facebook browser work. A browser recognition check ends after identifying
the available route. Only an authorized live Facebook run needs to open the page and verify posting
identity. Dry runs and Sheets-only repairs skip discovery.

1. **Attached tab.** For a user-supplied tab mention, bind it directly using
   `cua.getTab({mention: fullMentionUrl})`. Check the returned browser against the current
   Chrome extension inventory. Keep the user's choice of profile. If the tab is on another
   page, leave it intact and use the bound browser to open the fixed target in a new tab.
   If the mention is stale or belongs to another provider, report that specific problem.
2. **Existing binding.** Within the same chat, reuse a still-live, verified Chrome extension
   binding and a usable target tab. A tab closing only requires looking up tabs in that
   browser. Apply the user's latest tab/profile choice first. A numeric ID in an old run
   file is historical evidence, never a live binding.
3. **Fresh discovery.** With no usable binding, start with `cua.getState()`. Use its browser
   inventory and current returned documentation. The following pure JavaScript operates on
   that snapshot in the REPL. Pass a profile name only when the user specified it. It returns
   the intended operation without navigating or changing the browser.

```javascript
function findXinbadaChrome(browsers, requestedProfile) {
  function isTargetTab(tab) {
    try {
      const url = new URL(tab.url);
      const ids = url.searchParams.getAll("id");
      const origins = ["https://www.facebook.com", "https://facebook.com", "https://m.facebook.com"];
      return origins.includes(url.origin) && !url.username && !url.password &&
        url.pathname === "/profile.php" && ids.length === 1 &&
        ids[0] === "61589310638473" && !url.searchParams.has("sk");
    } catch {
      return false;
    }
  }

  const connected = browsers.filter(b => b.type === "extension" &&
    (b.family ? /^chrome$/i.test(b.family) : /^(google )?chrome$/i.test(b.name || "")));
  if (!connected.length) return {action: "chrome_missing"};
  const matching = requestedProfile === undefined ? connected :
    connected.filter(b => b.profileName === requestedProfile);
  if (!matching.length) return {action: "profile_missing"};
  const choices = matching.map(b => ({browserId: b.id, tabs: b.tabs.filter(isTargetTab)}));
  const candidates = choices.length === 1 ? choices : choices.filter(c => c.tabs.length);
  if (candidates.length !== 1) return {action: "choose_profile"};
  const {browserId, tabs} = candidates[0];
  return tabs.length === 1 ? {action: "reuse_tab", browserId, tabId: tabs[0].id} :
    {action: "open_target", browserId};
}
```

Use a successful browser inventory with per-browser tab lists. If a partial result leaves the
eligible browsers or required tabs unknown, refresh the missing list with the documented
`cua.listBrowsers()` or `cua.listTabs({browser: browserId})`. An app-only inventory error
does not invalidate a successful browser list.

| Result | Next operation in an authorized live run |
| --- | --- |
| `reuse_tab` | Bind `cua.getTab(tabId, {browser: browserId})` and check the visible page. If the tab disappeared, refresh that browser's tabs once. If it now shows other work, leave it intact and open the target in the same browser. |
| `open_target` | Open `cua.createBrowserTab(browserId, targetUrl, {sessionName: "🌿 辛巴达发布"})` with the exact URL from `publishing.md`. Empty tabs, unrelated pages and duplicate target tabs all allow a new dedicated tab in the identified browser. |
| `choose_profile` | Several eligible profiles remain. Ask for the intended Chrome tab or profile. |
| `chrome_missing` or `profile_missing` | Allow about five seconds for connection, refresh the browser inventory once, and apply the same selection again. If still missing, say whether Chrome or the requested profile is absent from this chat and suggest attaching the intended tab. |

Always read the selected tab's visible identity and permission as specified in
[publishing.md](publishing.md#one-identity-switch-sequence). A Facebook home tab, post
permalink, page title or extension profile name alone does not establish the active posting page.
When recovering after a submission, use the chosen browser for verification or reconciliation
of that submission. An existing composer or an interrupted submit must not trigger another post.

Record the selected browser name/type, returned browser ID, selection reason and any failing
operation in batch evidence. Distinguish inventory failure, an absent connection, and an error
opening a tab in a connected browser. Store only the target-related proof and omit unrelated
tab URLs, account details and raw inventories.
