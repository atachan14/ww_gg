## 最終ローカル検証（2026-10-16）

既存仕様のBフロー移行を実装。全646テストは504.400秒で成功。
元の期待値・計算予算は変更していない。基準再構築と内部再利用の比較も成功。

追加の保存Board経由7人混成ケースは既定20秒で
`observed_prior_private_ledger_budget_exceeded` のFuturePendingとなった。
単体カーネル経由7人回帰の成功とは別であり、大規模な保存Board評価の性能制限として残る。
計算済み親重みを正本とする差分更新は導入していない。
完全入力一致での内部再利用は導入済みで、以下の過去チェックポイントの
「cache最適化未導入」「検証中」等の進捗記述は履歴である。

未決の真偽優先順、CO配置・将来CO戦略、過去再評価・GameTree UIは追加していない。
push・deploy・公開は行っていない。

---

# B案ローカル移行の実装と検証

保全：ec513c2eb60bd20d5dbfbbe6c29bceb5648ff049。
保全ブランチ：safety/b-design-before-implementation-20261016。
作業ブランチ：work/board-flow-b。push/deploy/公開は禁止を維持。

## 共通の責任境界

- BoardData/GameData：共通の配役・Rulesを参照し、Boardには入力・必要履歴を保持。
  通常更新と訂正は同じ根拠再構成。Cookieの既存形式は移行adapterで維持。
- board_roles.reconstruct_roles：保存／生成Boardの共通3a入口。
  保存は根から有効入力を再生。生成はSavedOriginと行動・観測・公開報告・本人条件・
  情報縮約の根拠レシピを再生。親の計算済み重みを正本にしない。
- 3b：準備済み状態から候補・物理枝を評価。枝確率×子値を集約。
  生成子の具体化は3aへ戻る。既存の厳密なスカラ縮約・数学的評価カーネルは維持。
- 互換API：seer_manual、model_a_public、private_adapterは3a準備へ委譲。
  GameDataのない低レベルAPIは明示された初期共同分布をKernelOriginとする。
  HTTPの保存盤面／本人Tableは保存根拠を持つSavedOriginを用いる。

## 維持した意味

公開Q、秘密履歴混合、物理P、本人条件を分離。
取得前の根拠から再生して二重取得しない。公開報告の生成と手入力観測を区別。
過去の政策・proof設定はイベント時点に固定し、後の反実仮想を過去へ漏らさない。
同じ役職分布の疎形式／完全形式は意味で比較し、実際の物理枝参照を保持。
ゼロ支持・未対応・予算不足を0%で補わない。新しい真偽優先・将来CO・役職は追加しない。

## 比較

- frozen v0.5.1 replay oracle：tests/fixtures/board_replay_v051.py。
- 既存17ケースの各再生を旧実装と比較。
- 生成子の二行動を根拠起点から再生し、二つの物理遷移が再実行されることを確認。
- 生成公開報告・本人条件を旧カーネルと比較。
- 終局Boardは未来生成なしで基底値を返す。

## 検証記録

前段階：全639テスト成功（365.066秒）。
未来移行後の重点28テスト成功（34.595秒）。
終局基底ケースの追加1テスト成功（0.022秒）。
最終全テスト：実行中。ログ .artifacts/integration-validation/b-final-full-tests.log。
画面QA・最終commit：未完了。結果確認後に更新する。

## 残る仕様・範囲

新しい真偽優先・COgroup位置の変更、将来CO方針、Currentによる過去再評価式、
新GameTree機能は未決／未実装のまま。既存仕様の移行と混同しない。
新たな差分・cache最適化は未導入。再構成により計算コストは増えるため、速度改善は主張しない。


## チェックポイント2（最終回帰で差を検出・未完了）

未来生成子の入力・観測・公開報告・本人条件・情報縮約のレシピを導入。
共通 `board_roles.reconstruct_roles` から根拠起点＋履歴を再生するよう接続した。
公開互換APIも3a準備へ委譲。最新19676の18801で基本ブラウザQA成功。

最終全体：641件、520.165秒、5失敗・4エラー。合格扱いしない。
追加の終局基底1件は単独成功（0.022秒）。
ログ：`.artifacts/integration-validation/b-final-full-tests.log`。
前段階639件成功は未来移行前の結果であり、現差分の合格証明ではない。
実装差分は未コミット。保全ec513c2とsafetyブランチは保持。

### 差と次の優先確認

1. `ConditionEvidence.__call__` は常にsource.physicalを物理基底にするため、
   公開想定から別行動者を評価する反実仮想で、実枝の生存狼数制約と
   公開側の候補が異なる場合に Count and joint distribution disagree が起きる。
   既存の物理継承を捨てず、条件記録に「実枝の物理基底」か
   「公開想定から作る反実仮想基底」かの出所を明示する必要がある。
   target.physicalとの一致検証で種別を確定し再生する候補。未修正。
2. frozen kernel snapshotでmemoize_flows=Falseにした変更を確認。
   既存の同値memoを無効化したため予算超過を生んでいる可能性がある。
   B案の根拠再構成と、新しい差分cacheの導入を混同せず、既存の
   完成カーネルmemoを保持することを検討。予算値を上げて隠さない。
3. 本人占い／複数狼／霊COケースの新しいPendingを個別に再現し、
   SavedOriginとpublic/privateの記録が一致するか確認。
4. 9件修正後の重点再検証・全体回帰・最新サーバー再起動・commit。

### 現在のサーバーと証跡

PID19676、`b-help-server.py`絶対パス起動。3feature flagはwsgiと同じ。
URL `http://127.0.0.1:18801/` と `/help/program/board-design`。
ブラウザ証跡 `.artifacts/integration-validation/b-local-browser.json`。
PC1366・狭幅390/320・dark390、7/15・進行・本人狼率1・公開非変更が成功。
ただし上記9件をこの基本QAで網羅したとは扱わない。
全テストsession42615は終了。現在走っているテストはない。
アクセス拒否／仕様判断待ちの阻害はなく、残件は実装不具合と予算回帰。

### 失敗一覧

- ERROR: test_fixed_seven_player_case_completes_all_rows_under_default_budget (test_mixed_flow_memo.MixedFlowMemoTests.test_fixed_seven_player_case_completes_all_rows_under_default_budget)
- ERROR: test_high_player_ids_dynamic_fields_cache_and_terminal (test_seer_manual_general.SeerManualGeneralTests.test_high_player_ids_dynamic_fields_cache_and_terminal)
- ERROR: test_no_repeat_six_player_two_gj_replay_matches_inactive_role_reference (test_uniform_fixed_backup.UniformFixedBackupTests.test_no_repeat_six_player_two_gj_replay_matches_inactive_role_reference)
- ERROR: test_terminal_day_full_observation_history_matches_unreduced_execution (test_uniform_terminal_cut.UniformTerminalCutTests.test_terminal_day_full_observation_history_matches_unreduced_execution)
- FAIL: test_saved_reentry_two_gj_private_back_and_corpse_edit (test_guard_no_repeat.NoRepeatGuardRouteTests.test_saved_reentry_two_gj_private_back_and_corpse_edit)
- FAIL: test_budget_pending_and_recovery_with_cache (test_seer_manual_general.SeerManualGeneralTests.test_budget_pending_and_recovery_with_cache)
- FAIL: test_requested_five_player_same_white_co_example_and_terminal_branch (test_seer_multiple_wolves.MultipleWolfSeerTests.test_requested_five_player_same_white_co_example_and_terminal_branch)
- FAIL: test_public_co_scope_secret_history_none_and_public_cookie_identity (test_seer_view_forecast.SeerRouteTests.test_public_co_scope_secret_history_none_and_public_cookie_identity)
- FAIL: test_co_changes_probability_and_comparing_ccos (test_v03.ClaimWebTests.test_co_changes_probability_and_comparing_ccos)


## チェックポイント3：前回9差の修正、全646件を再検証中

前回の5失敗・4エラーはいずれも対象検証で成功を確認。
主な修正：
- ConditionEvidenceに実物理基底／公開想定からの比較用介入基底を記録。
  公開側の人数候補を、実枝Pの人数制約へ無条件に押し込まない。
- 3a内部の履歴再生が再度B案子再構成を起動する入れ子を抑止。
- 本人observer用には公開評価専用の縮約を適用しない。
- 本人→公開方針の仮想評価はPublicViewEvidenceで秘密条件を外してから縮約。
- 報告maxの未選択指示候補もMediumInstructionEvidenceとして記録。
- 公開の占い報告候補と、本人の物理観測後の報告更新を別の根拠で記録。
- 完全観測を残す場合／終局値だけ求める場合のterminal_payoffsと観測生存を記録。

### 性能・内部再利用

予算上限は変更していない。7人ケースは作業量250000のまま診断すると
約21.515秒で完了し、既定20秒への時間退行だった。
既存memoの維持に加え、完全入力・方針・profile・観測モード一致のイベント、
および同じ完全再構成入力の完了済み内部ステップだけを再利用。
EvidenceKeyは構造等値を検査し、同じ役職周辺率でも異なる秘密履歴を区別。
原点・全根拠の基準再構成は残す。reconstruction_kernel_reuse(False)で
新しい内部再利用を無効にした基準計算と比較するテストが成功。
実際の物理枝Pは置換せず、明示分布が完全一致する初期Q/Pだけ生成を省く。
新しい役率の差分更新方式を正本にしてはいない。

### 実測と進行

- 既定20秒の7人ケースを含む6件：17.960秒で成功。
- 後続の7人ケースはさらに高速化後も成功。
  同時追加したキー検証fixtureのprefix不備を修正し、その単独テストも成功（0.016秒）。
- 全646テスト実行中：session51088。
  `.artifacts/integration-validation/b-verified-full-tests.log`。
  チェックポイント作成時点でFAIL/ERRORなし（完了確認はまだ）。
- 前の失敗全体ログは診断履歴として残す。新コードの失敗件数に混ぜない。

### 次にすること

1. session51088の完了確認。新たな差があれば期待値を変えず修正。
2. 最終コードでPID19676の所有元を再確認し、18801だけ再起動。
   現19676はチェックポイント2時点のコードをロードしており最終コードではない。
3. 基本4viewport QAに加え、霊COの1/2、占い本人・複数狼の5/6等の
   修正ケースのHTTP/画面確認。HELPの検証中表記を最終結果に合わせる。
4. ソース・比較テスト・文書のみを選別してローカルcommit。
   `.artifacts/` と `docs/previews/` はstageしない。保全ec513c2は保持。

表示用RoleStateは無縮約の保存根拠から求める。既存評価器の役職縮約は
評価専用の十分な状態であり、そこから表示用の役職率を作らない。
将来GameTreeの未来盤面表示、新CO方針、新真偽優先規則は今回追加していない。
外部阻害・新たな仕様判断待ちはない。実装差分はまだ未コミット。
