# HELP bookshelf and phase-flow integration

Integrated into the recovery copy after the separate HELP worker stopped. Calculation code is unchanged in this stage. Shared Header is one partial; TOP/MAIN use its HELP link without a duplicate footer link. HELP pages share a bookshelf with server-rendered current-page state. Intro/examples, the four-column six-stage sample2 and medium sample3 use the approved prototype content; specs/program pages keep the existing dynamic native content, source/audit references, escaping and current/implemented/design distinctions.

app.py adds the examples/medium HELP pages and a strict asset allowlist. No general filesystem-serving route was introduced. The right-pane breadcrumbs are absent. Desktop uses the bookshelf to indicate location; mobile keeps article text within the viewport and scrolls only the wide flow diagram horizontally.

## Measured spacing

The empty #calculation had height68px, padding8px top/bottom, and the description margin was16px. The article parent had no contributing padding/gap. Empty stages now hide the equation element and use an8px description margin. Figure-to-description distance was84px and is now8px on1366/1920px PC. On390px it was115.1875px and is now31.1875px, including the needed horizontal-scroll hint. Equation stages retain natural content height:46.1875px on PC,40.59375px on mobile, with no overlap. Parent/figure/equation/description computed geometry is saved in task-6/help-browser-validation.json.

## Validation

- Installed Edge headless at dedicated18801:1366x768,1920x1080,390x844, all six stages,18 full-page screenshots plus6 mobile right-edge screenshots. All inspected via contact sheets. Four Phase columns and node centers, visible nodes, values1/0,1/3,1/5,4/15,7/15 and46.7%, reverse contributions, absence of breadcrumbs/current bookshelf selection, no page-wide horizontal overflow were verified.
- Arbitrary stage jumps,60 rapid clicks, ArrowLeft, reload preserving selected stage, shelf navigation and browser-back passed. TOP->MAIN->HELP->MAIN preserved the7/15 game value. No JavaScript page errors.
- Medium page: all five stages at all three widths,15 screenshots; PC/mobile contact sheets inspected, back navigation verified. All9 medium declaration configurations match the existing core's complete role support and exact normalized mass. Existing medium JS/CSS/fixture logic was copied without numeric edits.
- HELP/program route+link+anchor+readonly-session+escaping tests:11 passed in1.232s. Final full regression is recorded below when complete.
- Prototype mirroring is confined to the explicitly authorized G:/source/repos/Python/ww_gg/.artifacts/probability-model-guide folder: breadcrumbs removed from user-facing HELP pages, same spacing override appended to help-shell.css. All18 prototype width/stage combinations passed after this mirror; old G repository core/configuration untouched.

Computer Use could not initialize because its Windows runtime directory was missing (HRESULT0x80070003). Existing installed Edge/Playwright browser validation was used successfully; no permissions or Git settings were relaxed. Ordinary managed approval calls can read/write this recovery worktree and inspect the dedicated server. Sandbox-only git calls may report not-a-worktree, so Git operations used the same existing approved execution path.

No push/deploy. Version badge remainsv0.4 until the user agrees to a release. Item-I completion has not been removed from the release gate.

Final verification: all593 tests passed in262.810 seconds (task-6/help-integrated-full.log), including backend exact/profile/history regressions and HELP link/anchor/session checks. This is the final integrated executable code; later changes are documentation only. The dedicated preview and final local commit are reported in the task outcome.
