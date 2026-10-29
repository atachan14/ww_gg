> **訂正（候補方針の整合性）**: 以前の5/6人「未定義候補」例は、物理側だけ別行動に変え公開側を元の仮方針に固定した比較に由来していました。最大化の合法候補は戦略の範囲内です。これを仕様上不可避な想定外、新しい信念ルールが①完了に必須、という根拠にはしません。候補ごとに同一情報集合の方針を一貫して置換し、公開支持と物理枝を揃える修正を検証中です。実際の入力矛盾とは区別します。詳細は [candidate-policy-coherence.md](candidate-policy-coherence.md)。

# 根の完全秘密状態を使う均等継続入口

基準40fcaaa。既存画面の固定CO評価は変更せず、root_secret_flowの明示的な補助APIとして追加。

prepare_root_secretsは初日・全員生存・死亡履歴なしのBoardからtracked=NoneのTrueScanStateを作り、
既存acquire_uniformで全真占いの初日結果を生成する。random_white/normal/noneの規則を維持。
市民2・霊能1・占い1・狼1は60配役180状態。P1真占いの条件で12配役36状態。
各世界で非狼3人各1/3、位置P2～P5各1/4、対象役は霊能1/3・市民2/3。
initial_random_whiteと一致する。

RootSecretBranchは公開Board/public_lawと物理Board/physical_lawを分離する。
observe_root_publicは既存model Aで更新済みのBoardと公開観測互換性の述語を受ける。
公開役職重みを外側に維持して世界内秘密履歴を条件付け、物理質量から物理分布を別に条件付ける。
公開重みが残る世界の秘密支持ゼロはPending。政策選択尤度を公開役職重みに掛けない。
死亡によるphase/alive/history変更はstep_root_actionによる継承を先に使う。
root_actor_viewは本人の観測述語を共通条件付けへ渡し、主観beliefと条件付きphysical_lawを分離する。
呼出側は本人に属する情報だけで観測述語を作る。

step_root_actionは固定行動の介入で、共通resolve_actionと能力・死亡・観測・朝の処理へ接続。
root_secret_valueは均等処刑/襲撃による最終村勝率を継承した物理分布で評価する。
この入口では潜伏占いの取得や履歴を省く値縮約を使わない。死亡後の過去結果も保持する。
新経路のmaxはPending。既存maxは維持する。
policy_choiceは既存処刑/襲撃の最適同率選択だけを共通化する。
処刑は公開分布で村勝率最大、襲撃は狼情報集合で村勝率最小。
候補・合法手・情報集合・採点測度は呼出側に残し、設定外の戦略は追加しない。

全開示で初日の公開結果が不足する場合はfull_disclosure_truth_not_conditionedを維持。
公開記録と真結果互換性を明示すれば共通朝フローへ接続できる。
将来CO、途中盤面の再構築、新しい秘密戦略は未実装。
狩人を含む初日占い生成は可能だが、新経路の狩人継続/無死亡後公開履歴混合はPending。
自噛み可能な規則に対して政策が自噛みを除く組合せも、支持接続未対応としてPending。
規則上可能な狼死体をmodel Aが残す一方、その政策では選べない世界の秘密履歴支持を新規配分する必要があるため。
一様な仮履歴は補わない。連続護衛なしの前夜護衛や未公開結果も異なる合法手/情報集合のまま圧縮しない。

検証: 関連33テスト、新入口/HELP12テスト、全508テスト成功（136.613秒）。

## 初日均等の既存画面への接続

evaluate_public_gameが呼ぶ入口で、root_screen_eligibleの対応条件を判定する。
初日・全員生存・占い師あり・狩人なし・占いCOなし・処刑/襲撃とも均等が基本条件。
霊能COかつ全開示で偽報告maxが必要な条件、自噛み規則と政策の支持接続未対応の条件は切替対象外。
対応範囲では完全秘密分布を生成し、全体勝率・対象別行・朝までの値を同じ共通継続で計算。
計算量が予算を超えたときはPendingを返し、秘密を省いた旧数値へフォールバックしない。
既存max、固定CO、途中盤面は従来入口を維持。セッションへ秘密分布を保存せず、公開キャッシュへ本人情報を入れない。
この小段階で接続するのは初日の公開画面評価。操作で進めた途中盤面の再入場や潜伏占いの秘密視点Tableは未接続。

## 設定戦略との対応監査

- day/night random: 合法候補を均等。max: 設定済み継続方針で候補を採点して陣営目的の期待値最大候補を同率均等。
- seer_position: 本人の未訪問先を優先して均等。初日normal/random_white/noneはRulesの規則。
- guard_position: 対応済み範囲で均等。連続護衛の規則はscopeで判定し、新規規則を仮定しない。
- disclosure_common/役職別disclosure: none/all。COは固定で将来COを生成しない。
- fake_seer_policy: 設定済みuniformまたはnoncontradictory→uniform。複数偽報告の未定義共同分布はPending。
- fake_reports: 既存の霊能報告候補をrandom/maxで選ぶ。未設定の報告方針は作らない。

同時に複数の期待勝率最大化を行う一般の相互最大化は未実装。戦略拡張時の課題であり、定義済み均等の実行要件ではない。

画面接続検証: 関連24件、HELP説明更新後4件、全512テスト成功（150.114秒）。

## 2026-10-14 normal root and later-night checkpoint

- Normal C/H/W day-max/night-max entry now uses complete unique profile certification. Both guard-repeat rules pass the route regression. Existing initially known-hunter max entry remains intact.
- Full regression: 586 tests passed in 244.931 seconds (root-profile-integration-full.log). Following the UI-only dawn-form extraction, the route regression passed in 8.977 seconds and static/app.js passed node --check.
- Dedicated 18801 browser validation, C2/H1/W1, no repeated guard: P1 hunter claim and P4 execution give public night value 1/10; wolf P1 legal targets P2/P3 each give 1/6. Normal GJ report then advance gives Day2 value 1/2. Reload preserves 1/2; back restores night 1/10 and both max policies. Night Board now exposes the existing dawn observation controls through shared partials.
- A later Day2 night with six retained joint histories is certified uniquely by policy-independent score proof (729 possible profiles, one evaluation). Five-player coupled root remains budget-unfinished; six-player root domain is 759375. Neither installs an uncertified kernel or substitutes values.
- RETRACTED: the initially known-hunter candidate-GJ refusal mixed the selected public profile with a different physical action. The coherent candidate comparison now preserves the legacy village value 1/4; it is not a required new off-path belief rule.
- Remaining: coupled later-night budget coverage and seer/medium six-player integration. Overall integration is unfinished; publication remains held. Dedicated preview PID 20352; no push/deploy or shared settings changes.

## 2026-10-14 coupled-profile cost measurement and pure branch reuse

- cProfile, unchanged 20-second profile budget: five-player C/H/W max/max root has 2401 candidate profiles. Its initial deviation immediately depends on a later proof; 223 nested profile evaluations reached the deadline, with one unique child certificate and no installed root kernel. Of the approximately 20 seconds, resolve_action accounted for 15.1 seconds, including guarded_outcomes 8.5 and repeated exact Board/action construction. Six-player root is different: its 759375-profile domain is rejected by the count cap in about 0.012 seconds, not by a slow completed numerical search.
- Candidate engines now share only pure physical/public branch construction in the resolver's bounded request-local cache. Keys retain Rules, Strategy, the complete Board, target and (for public branches) full guard state. Profile-dependent scores, public support kernels, owner restrictions and incomplete computations are not shared. Errors never install cache entries.
- The measured post-change 20-second diagnostic still remains budget-unfinished (280 nested evaluations, one unique child). These deadline-truncated runs do not prove overall speedup or root completion. The six-player count barrier is unchanged. Tests explicitly verify cross-profile reuse, separation of changed role support and failure non-caching.
- A separate latent-seer six-player day-random/night-max diagnostic remains Pending(root_guard_profile_budget_unfinished). Profiling locates approximately 5.1 of 6.8 seconds in physical_actor_outcomes during the pre-certificate candidate proposal, including 9989 action_outcomes calls. This is a further pure-physics reuse opportunity; acquisition/guard/attack histories must remain intact. No new value or off-path belief rule is supplied.
- Fixed-work diagnostic (max_work=2000): five-player pure-branch calls 384, exact cache hits 319, entries 65; still budget-unfinished, one unique child. This records actual reuse, not completion of the root proof.
- Validation: related 18 tests passed in 57.899s, additional branch-input separation test passed in 0.020s. Full 587-test run completed in 240.099s with four failures inherited from the prior UI-only checkpoint: three obsolete assertions that night BoardLog/GJ observations were absent, and one stale public/static mirror. Updated the observation assertions while retaining clearing/history checks, regenerated local static mirrors with build_vercel.py; all 25 dawn/deployment tests then passed in 2.777s. No calculation test failed. The full suite was not redundantly rerun after these test/mirror-only corrections.

## 2026-10-14 joint-history physical branch reuse

- physical_actor_outcomes now constructs casualties once per (complete role masks, complete guard history) within a fixed Board/action/rules/strategy/observer call. Scan records, past attack memories and hypothesis mass do not enter this physical resolver. Each original hypothesis is still separately carried into the result with its acquisitions and attack history unchanged and its own exact mass; nothing is marginalized for policy selection.
- New six-player W1/M1/S1/H1 regression compares the complete weighted output ledger with separately resolved singleton histories, including different scan records, attack memories and prior guards. It verifies both repeat-guard settings, exact GJ mass (1/5 with repeats, 1/8 without), and reduced guard resolution calls (10/8 instead of 20/16). All six fixed-actor tests passed in 0.462s.
- Same-input comparison against 70095d5, latent-seer six-player day-random/night-max: physical action_outcomes calls 9984 -> 912, fixed-guard resolutions 2752 -> 256. Diagnostic elapsed 2.518 -> 1.188 seconds is one local observation, not a performance guarantee. Both versions return root_guard_profile_budget_unfinished, with no invented value. Full final-code regression is being run separately.
- Role-matrix comparison: medium-only six-player has no scan-history duplication and keeps 912 action / 256 guard calls in both versions. Seer+medium six-player reduces 29952 -> 2736 action calls and 8256 -> 768 guard resolutions. Both still return the same budget-unfinished status; no profile is certified by these cost measurements.
- Final-code full regression: all 588 tests passed in 239.672 seconds (joint-physics-reuse-full.log), including the four corrected UI/static checks from the preceding checkpoint. No templates, HELP assets, CSS or UI JavaScript changed in this stage. Five/six-player coupled certificates remain unfinished and publication remains held.

## 2026-10-14 terminal dependency classes and refusal witnesses

- The five-player day-max/night-max root previously stopped at 485/2187 profiles in its first coupled later night. Where every possible next execution physically terminates and no public ability report is active, a fixed night profile affects the common candidate values only via the complete public Board after GJ. A request-local score-class memo now retains full public Boards and computes the first class's complete vectors through the original common flow. Original joint acquisition/guard/attack ledgers are still carried; no replacement game model or scalar constants are used.
- Actual five-player rerun completed three later contexts of 2187/2187 candidates, each with one unique certificate. Selected vectors are independently recomputed by ordinary FixedPublicWolfProfile actions for every legal deviation in tests, both guard-repeat rules. Bounded six-player public-cast subcases with seer only, medium only and both also match ordinary full-joint common-flow vectors; these are NOT the unrestricted six-player cases.
- RETRACTED: the prior five/six-player undefined-candidate claim and its purported off-path-rule requirement were based on different physical/public candidate policies. They do not establish an unavoidable undefined observation or a reason to defer item I. See [candidate-policy-coherence.md](candidate-policy-coherence.md) for the corrected contract and legacy 1/4 minimum.
  - Unrestricted latent seer six-player, medium six-player, and seer+medium six-player day-random/night-max remain root_guard_profile_budget_unfinished in the ordinary public entry. Local observations: about 6.8s / 0.8s / 20.5s respectively, not runtime guarantees. Full-joint mixed-role coverage is unfinished. Additional Model-A changes, max replacement, shared permissions, push/deploy and HELP edits remain out of scope.
- Final regression for this code: all 592 tests passed in 266.863 seconds (terminal-profile-classes-full.log). No route/template/HELP/static files changed. Current stage can hand route/HELP ownership to the separate integration task after this local save.
