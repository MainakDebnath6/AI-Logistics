# Test report (commands actually executed)
| Suite | Command | Result |
|---|---|---|
| Backend (all) | `python -m pytest -q` (repo root, branch research-final) | **88 passed, 1 failed** (baseline before changes: 86 passed, 1 failed; +2 new tests). The failure `test_development_demo_seed_is_idempotent...` is environmental: passlib + newer bcrypt in the sandbox ("password longer than 72 bytes"); it is unchanged from baseline and unrelated to this work. |
| Research module | `python -m pytest research_hccr/tests -q` (inside the repo) | **33 passed** (frozen-pipeline consistency, non-anticipativity, firewall, activation, mechanism/freshness/real-data checks) |
| Claim verification | `python -m research_hccr.verify_claims` | **144 checks, exit 0** |
| Frontend tests | `node --test` on the 3 test files | **9 passed, 0 failed** (baseline 8; +1 new) |
| Frontend lint | `npx eslint .` | 7 pre-existing errors (react-hooks rules), unchanged; changed files lint clean |
| Frontend build | `npx vite build` | success (chunk-size warning only) |
| LaTeX | pdflatex/bibtex x3 | 6 pages, no undefined references/overfull boxes |
Blocked / not run: end-to-end login, order/vehicle CRUD, live OSRM road routing, live-site checks, production deployment, database migrations against a live DB (no credentials or reachable services). One uninterrupted `--stage all` experiment run was not executed (stages ran resumably); sensitivity/forecaster stages were not rerun with the robust policy.
