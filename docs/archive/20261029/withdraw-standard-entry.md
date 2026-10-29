# 撤回後の履歴報告証明を標準入口で有効化

430566cで診断した局所修正を標準入口で有効化した。prepare_root_entry と replay_root_secrets の既定値が履歴報告の存在証明を使用する。旧動作は `_historical_disclosure_proof=False` を明示して再現できる。新たなCO/報告方針、配役重み、取得ルールは導入していない。

## 変更前後

| 項目 | 430566cまでの標準 | 今回の標準 |
|---|---|---|
| 初日CO/報告を後日withdrawした4人・6人例 | full_disclosure_truth_not_conditioned | SavedOrigin/registryで再構築成功 |
| 過去の報告存在 | 公開役職判定だけで使用 | 同じ既存事実を秘密ガードにも渡す |
| 現在有効な具体的報告 | 空 | 空のまま |
| 4人公開狼率 P1/P3/P4 | 3/5・1/5・1/5 | 同一 |
| 過去に未報告だったCOの偽判定 | P1狼率1 | 同一。真占いの救済なし |
| 対象例の秘密joint | 標準ではPending | 独立列挙と一致する10状態/116状態 |

存在証明は報告者と取得日だけ。対象/色を秘密履歴へコピーせず、未知の取得は元の配役・ルール・設定済み方針から生成する。4人のP1真占いの初回対象は2/3/4を支持し、旧P3白には固定しない。

## 既知障害回帰の明示移行

既存23本中22本の期待値は無変更。1本だけ、旧 `test_late_co_common_pending_preserves_input_and_can_be_undone` を新 `test_standard_historical_withdraw_resolves_legacy_pending_and_can_be_undone` へ改名・移行した。新テストは標準成功、入力不変、withdraw batch削除による厳密復旧を要求し、明示Falseの旧replayでは以前のPendingも確認する。削除して通したわけではない。

診断回帰も「標準Pending」から「明示FalseはPending、標準は成功」へ明示変更。公開役職率のoracleは変えていない。4人5配役/6人8配役のマスクと重みを手書き列挙し、初回白・未訪問優先・死亡前取得・夜の攻撃履歴を別に列挙した。修正済み共通コードと切り出し型同士の一致だけを正解根拠にしていない。

旧 `withdraw-prefix-results.json` は430566cの証拠のまま保持し、新結果は `withdraw-standard-results.json` に分離した。

## 正式経路と有限検証

標準SavedOrigin、6人registry、RoleState.forecast、cold再構築/cache、正式private条件付けを確認。本人が明示した初回P3白なら本人視点のP4狼率1、別の合法なP2白ならP3/P4各1/2となり、公開入力や分布を変えない。退役した公開P3白を本人秘密へ戻していない。

均等方針の手計算とも一致：3人生存の夜・狼1は村勝率0、4人生存の昼・狼1は1/4。6人例の現在行動値はP1=5/8、P4/P5/P6各1/8。主要/累積値・完全Table・個人相関・物理枝massの既存比較も維持。

再現: `python -B -m benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture`。移行後の既存23＋独立列挙等5＋既存意味3＋正式root経路9＝40テスト成功。各run30秒/全体300秒/WorkingSet1.5GB停止。今回 24.235秒、peak 53.4MiB。全suite・長時間workerなし。ログ `.artifacts/withdraw-standard-final.log`。

## 解消済みと残件

解消済み：履歴上は報告済みの初日CO/報告を後日withdrawしたときの偽の full_disclosure_truth_not_conditioned。標準SavedOrigin/forecast/6人registryで解消した。

正当なPendingは維持：報告が実際に必要なのに未条件付けの真占い支持を渡した場合、公開支持が正でも合法な秘密履歴がゼロの場合（未訪問対象が残るのに同じ対象へ再占いした入力など）。一律補完や戦略の均等化で数値を返さない。

未実装のまま：夜snapshot入力編集、実UI所有元切替/archive統合、全終端木の効率的ラベル復元、snapshot-localな公開信念cache bridgeの物理経路mass、7人/max/狩人への新規拡張。既存max拒否とguard-only正式回帰は維持確認したが、新規対応を主張しない。

UI・公開設定・サーバー・共有権限は変更せず、push/deployなし。標準入口のローカル修正と回帰移行を独立commitとして区切る。
