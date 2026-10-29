# Publication proof cost / separation audit

Audited f4551d4. No initial Forecast was run and no production code changed in this audit.

The 37 player exchanges are exclusively in cut_out_seven_publication_fixture.audit's assertion loop using moved_law. InheritedGroupRegistry.publication does not call that function, enumerate player permutations, compare candidate groups, canonicalize states or reconstruct the initial root. Its group update uses the existing parent witness and point-fixes the newly reported/resolved endpoints.

A focused regression wraps every publication call in the two-action/one-morning case. During each call it makes moved_law (including the fixture alias), initial_board, combinations and ConstructiveCutOutGroups.__init__ throw if called. All publication calls complete successfully; the later test-only 37-swap validation also completes. This separates actual publication work from verification work instead of merely counting calls after both have run.

## Exact reconstruction cost: a qualification

It would be incorrect to claim that the current output check performs no full-history scan. replace_worlds builds a temporary Board through dataclasses.replace. Board.__post_init__ scans the retained history to validate PublicEvent types and to collect/check the complete dead-player set against alive. In this hunter-free case these are two history passes. It also projects/validates the supplied child world distribution and derives the live wolf-count summary. Full Board equality checks immutable fields and distribution tuples. New-past prefix and report-resolved set checks also read existing record collections.

None of this replays history to generate secret distributions, tries player relabelings, recomputes an initial prior, or searches for a group. The public worlds are the existing event generator's output. The reconstruction is an additional consistency validation of that output against the parent's fixed Board facts, but it has O(history + world/record data) work and allocation; it is not constant-time or delta-only. Its performance impact has not been measured. Any later removal of that duplicated validation needs an equally strong trusted-event receipt or a separately checked derived-field proof, not blanket permission to change wolf_count.

Two related local regressions passed in 0.148 seconds, peak working set 36,286,464 bytes. Existing malformed CO/cancellation/history/phase/derived-count checks remain included. No canonical/CandidateRules fallback was added.

## Next initial comparison readiness

The first legitimate medium publication proof boundary is repaired and locally tested. The dedicated initial public/uniform entry and the capped runner remain ready. The last actual initial comparison remains unverified: inherited stopped at the now-repaired boundary, and independent hit its five-second budget. Later inherited boundaries and all final equality items remain unknown.

Wait for Morishi's UI measurement to finish and explicit coordination before running the next initial case. Proposed unchanged limits: each route 5 seconds, worker 30 seconds, memory 1.5 GB; compare Table/joint, branch mass and terminal readbacks, with timeout/uncompared treated as unverified. Ordinary UI, initial max and public version remain unchanged.