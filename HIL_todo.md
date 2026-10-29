# HIL Todo — Grove

> Items requiring human verification or judgment before proceeding.
> Format: `- [ ] REFERENCE — issue description — suggested fix or next step`

---

## Open Items

### Module Split: Missing Implementations

- [ ] **export-scheduler** — `export-scheduler` is documented in CHEATSHEET.md and referenced in `src/shared/manifest_bridge.py` (line 8) but `do_export_scheduler` was never implemented in `manifest.py` — implement `do_export_scheduler` during the manifest.py module split; `manifest_bridge.py` already contains the bridge logic to connect to the scheduler

---

## Resolved Items

*(Move entries here once verified and fixed upstream.)*

---

## Notes

- `manifest_bridge.py` at `src/shared/manifest_bridge.py` contains the scheduler export logic; `do_export_scheduler` should call into that module
