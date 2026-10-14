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
- The separate initially known live-hunter counterfactual GJ case has genuinely zero public support under the selected profile. It remains undefined/Pending; no new off-path belief rule is supplied.
- Remaining: coupled later-night budget coverage and seer/medium six-player integration. Overall integration is unfinished; publication remains held. Dedicated preview PID 20352; no push/deploy or shared settings changes.

## 2026-10-14 coupled-profile cost measurement and pure branch reuse

- cProfile, unchanged 20-second profile budget: five-player C/H/W max/max root has 2401 candidate profiles. Its initial deviation immediately depends on a later proof; 223 nested profile evaluations reached the deadline, with one unique child certificate and no installed root kernel. Of the approximately 20 seconds, resolve_action accounted for 15.1 seconds, including guarded_outcomes 8.5 and repeated exact Board/action construction. Six-player root is different: its 759375-profile domain is rejected by the count cap in about 0.012 seconds, not by a slow completed numerical search.
- Candidate engines now share only pure physical/public branch construction in the resolver's bounded request-local cache. Keys retain Rules, Strategy, the complete Board, target and (for public branches) full guard state. Profile-dependent scores, public support kernels, owner restrictions and incomplete computations are not shared. Errors never install cache entries.
- The measured post-change 20-second diagnostic still remains budget-unfinished (280 nested evaluations, one unique child). These deadline-truncated runs do not prove overall speedup or root completion. The six-player count barrier is unchanged. Tests explicitly verify cross-profile reuse, separation of changed role support and failure non-caching.
- A separate latent-seer six-player day-random/night-max diagnostic remains Pending(root_guard_profile_budget_unfinished). Profiling locates approximately 5.1 of 6.8 seconds in physical_actor_outcomes during the pre-certificate candidate proposal, including 9989 action_outcomes calls. This is a further pure-physics reuse opportunity; acquisition/guard/attack histories must remain intact. No new value or off-path belief rule is supplied.
- Fixed-work diagnostic (max_work=2000): five-player pure-branch calls 384, exact cache hits 319, entries 65; still budget-unfinished, one unique child. This records actual reuse, not completion of the root proof.
- Validation: related 18 tests passed in 57.899s, additional branch-input separation test passed in 0.020s. Full 587-test run completed in 240.099s with four failures inherited from the prior UI-only checkpoint: three obsolete assertions that night BoardLog/GJ observations were absent, and one stale public/static mirror. Updated the observation assertions while retaining clearing/history checks, regenerated local static mirrors with build_vercel.py; all 25 dawn/deployment tests then passed in 2.777s. No calculation test failed. The full suite was not redundantly rerun after these test/mirror-only corrections.
