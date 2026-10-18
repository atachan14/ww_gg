# Corpse scans and acquisition chronology

The user clarified: a dead target still yields its role color. Only a seer who died before acquisition has no new result. This is a semantic bug fix, separate from matching optimizations.

Day d execution precedes Night d acquisition (result slot d+1). Acquisition precedes night casualties. Owner or target death after acquisition never deletes an acquired record. Later death does not delete an already published result. Morning publication still requires a surviving reporter; no new disclosure by a dead reporter is fabricated.

Both fixed-CO and root use `scan_intervention_matches`, checking the owner's historical acquisition roster rather than current morning survivors. The old root target-death exemption is removed. True and fake scans choose from original players, excluding self and already scanned targets; corpses remain legal. Initial random-white law is unchanged. Guards and attacks still choose their existing living target domains. No new CO/report/max policy was introduced.

Regression covers owner/target alive/dead combinations before acquisition, later deaths, historical interventions, corpse public and private evidence, contradictory publication atomicity, back navigation, initial 12-role/36-secret-state law, and root/fixed-CO agreement.

The actual seven-player max example changes from 17/36 to **3487/7200** (+29/2400). This is a rule correction, not a cache equality claim. Corrected prototype: 49.755 seconds, peak working set 768,892,928 bytes. The labelled reference with retirement and physical caches did not finish within 75 seconds (peak 1,108,037,632 bytes); full original-reference completion remains unverified. All 128 completed conditional original-evaluator values matched under the corrected rule. Four small complete original-evaluator versus prototype comparisons match: uniform five 7/15, max five 1, medium/max five 1, medium/max six/two-wolf 1/4. Original numerical methods are inherited unchanged and all new optimization flags disabled in those references.

Evidence: `corpse-rule-seven-results.json`, `corpse-rule-seven-labelled.json`, `corpse-rule-branch-validation.json`, `corpse-rule-small-comparisons.json` under benchmarks/player_match_groups. Older JSON and 17/36 UI measurements remain historical. The old review-only target exemption is superseded and disabled.

The Edge tests exercise the Python server UI. They are not a Pyodide numerical backend test. Browser numerical backend selection remains unimplemented/unverified. Root seven-player key construction showed no material total gain and remains outside the local factory guard. Public/private general histories and broad hunter/GJ sharing are not completed by this fix.

Actual Flask NDJSON completed in 57.452 seconds, roles first, with every Table row equal to the corrected prototype. Isolated headless Edge on dedicated port18801 confirmed white corpse target4 remains selected and available, value1/3, and later owner death retains published evidence; no JavaScript errors. Evidence: corpse-rule-ui-seven-results.json and corpse-browser-results.json.

Validation: focused ability regressions 61 tests passed (11.124s); private/local/extension controls 32 passed (25.343s); all 13 tests in test_seer_manual passed. An additional unchanged legacy budget UI assertion in test_seer_manual_general expects the literal Japanese text for calculation budget, while current generic pending rendering omits that text. Its pending marker and hidden win value checks pass; this unrelated copy expectation still fails. The broader legacy manual/general run was stopped when it entered a long existing numerical case; no full-suite success is claimed for this milestone.
