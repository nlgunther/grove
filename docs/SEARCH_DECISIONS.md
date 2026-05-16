# Search Command — Decision Log

Tracks every place the implementation diverges from the brief, and why.

---

## D1 — `max_depth=1` instead of `max_depth=0` for node-only render

**Brief says:** Pass `max_depth=0` to `ManifestView.render()` when `--expand` is not given.

**Actual behaviour of render code:**  
The recursion starts with `current_depth=0` and immediately checks
`if max_depth is not None and current_depth >= max_depth: return`.  
With `max_depth=0`, `0 >= 0` is True on the very first call, so the matched
node itself is never printed — blank output for every result.

**Decision:** Use `max_depth=1`.  
At depth 0 the matched node renders; at depth 1 the check fires and stops
before any children appear.  This is what "node only" means in practice.

**Approved by:** Ken, 2026-05-16

---

## D2 — `--regexp` flag instead of removing `--ignore-case` entirely

**Brief appendix says:** Drop `--ignore-case` everywhere and replace all substring
matching with `re.compile` / `pattern.search()`.  The user controls
case-sensitivity via `(?i)` inline flag.

**Ken's decision:** Keep plain substring as the default (faster, no escape
issues for non-technical users).  Add a `--regexp` flag to opt into regex mode.

**Manifest search:**  
- Default: `term in value` (case-sensitive substring).  
- `--regexp`: compile `term` with `re.compile(term)`, catch `re.error` and
  print a clear message; match with `pattern.search(value)`.  
- `--ignore-case` is **not** added — case control in regexp mode is via `(?i)`.

**Scheduler search:**  
- Default: case-insensitive substring (brief specified "always case-insensitive"
  for prose tasks; preserved as-is).  
- `--regexp`: compile `term` with `re.compile(term, re.IGNORECASE)` so
  plain patterns still match case-insensitively, consistent with default
  behaviour.

**Approved by:** Ken, 2026-05-16

---

*Add new entries D3, D4, … as further deviations are discovered during
implementation.*
