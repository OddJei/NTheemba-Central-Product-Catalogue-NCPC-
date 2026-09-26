# Security boundary

- Tokens are never stored in plaintext; only SHA-256 digests are persisted.
- Business principals are fixed to one `business_id`; supplied tenant IDs cannot
  select another tenant.
- Admin/reviewer/Ntheemba behavior is scope-gated.
- Request IDs are sanitized; bodies and bounded lists have strict limits.
- A per-process limiter is a safety layer; production ingress must add distributed
  limits, TLS, network policy, and abuse monitoring.
- Public catalogue and wider-discovery DTOs are explicit allowlists.
- NCPC persistence and imports forbid price, cost, stock, availability, supplier,
  batch, sales, revenue, expense, profit, or margin authority.
- Audit events and released snapshots are protected against update/delete.
- Logs must record safe IDs/outcomes, never bearer tokens, raw evidence containing
  personal data, or TradeFlow business state.
