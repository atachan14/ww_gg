# Player／Boardリファクタ：段階5の最終確認

今回合意した5段階を、下記の限定範囲で一区切りにしました。既定ONや公開リリースの承認・実行ではありません。branchは `refactor/player-view-stage12`、全回帰で検証したruntimeは `68bf2f98b3eb2460fd784f904f517ee234a12644`。この最終チェックポイントでは検証scriptと結果・総括のみを追加し、その後にapp／werewolf／testsは変更していません。

| 段階 | 結果 |
|---|---|
| 1 保存・比較基準 | 完了。公開03e4e31を構造基準へ固定、各prototypeとc872d19の安全branch保持。未追跡成果物は保持しpreviewは別保存 |
| 2 責務・正本 | 完了。Game共通Rule/Cast、Board証拠／全体ログ／joint、視点別Player viewと派生値の対応表を固定 |
| 3 view／UI／行組立 | 完了。read-only view・被公開結果index、公開／本人UI読取、直接行組立へ整理。必要なJSON／旧保存読込／timeline境界は保持 |
| 4 一致group | 限定完了。内部明示切替のみ、既定OFF。公開・既知真占い・初日取得なし・均等・霊狩人なしの5/6人に限定。対応外は元設定の旧flow |
| 5 最終検証 | 完了。全回帰終端、既知失敗の理由照合、短い7人の基準/OFF/fallback比較を実施。新規regressionなし |

## 全体回帰の終端

`python -B -m unittest discover -s tests -v`

**754件、843.314秒、753成功、失敗1、エラー0。全件greenではありません。**

残る失敗は `test_seer_manual_general.SeerManualGeneralTests.test_budget_pending_and_recovery_with_cache`。HTMLが旧文字列「計算予算」を含むという期待値と、既存の計算作業量上限メッセージとの不一致です。同じtest名だけで既知扱いせず、AssertionErrorの欠けているbyte文字列まで既存03系の全回帰ログと一致することを確認しました。新しい失敗・エラーは0です。テストのskip、失敗の削除、UI文言の変更はしていません。

全回帰には既存suite自身の予算付き計算も含まれますが、指定7人重盤面の270秒ベンチを追加で繰り返したわけではありません。

全ログは `.artifacts/player-match-groups/full-regression.log`。SHA-256と分類は [final-stage5-checks.json](../benchmarks/player_view_refactor/final-stage5-checks.json) に記録。過去の728/740テスト結果と現在の754件を混同しません。

## 既定OFFとONの区別

既定OFFでは従来InformationSetForecastをそのまま選びます。保存互換、元ログの訂正取消・過去Board編集、公開／本人表示、roles先行、Pending、計算中編集、旧応答排除の検証を維持しています。直前のheadless Edge確認も同じ最終runtimeで全操作成功、pageerror0、専用18801 HTTP200でした。

ONは通常UI・保存設定に公開していない内部引数です。限定5人1狼7/15、6人1狼3/8、6人2狼1/12で最終値・Table全field・全まとめ対象枝の質量／joint／役職率／合法手／終端値が一致しました。6人の測定で行動展開・時間・Peak WSが減った結果は [限定接続記録](player-match-groups-optin.md) にあります。全ケースや通常UIの一律高速化を保証しません。

## 7人：短い有限比較

保存済みの7人重盤面入力に対し、各fresh子プロセスで以下を順番に比較しました。

1. git上の03e4e31の凍結public入口＋変更していない数理kernel。
2. 最終コードの既定OFF。
3. 最終コードへONを要求し、適用外としてfallback。

上限はそれぞれ**1000work／2秒、外側10秒**。三者とも役職率とPending理由・work停止が一致し、新group経路は無効でした。P1/P2占い1/2・狼1/2、P3霊1、P4市民1、P5～7市民2/3・狼1/3を保持しています。最終勝率は計算していません。

[7人短時間結果](../benchmarks/player_view_refactor/final-seven-short.json)、再現scriptは `check_final_seven.py`。

## 保存・adapter・残課題

- **本格的なPlayer行の永続保存形式変更はありません。** 保存の正本は現行Game/Board証拠・公開ログで、PlayerDataは現在表示するBoard／視点の派生read-only viewです。
- 外部JSON、旧保存読込、legacy public_log/base/batchesとgraphの互換投影、timeline生成器、明示的なrow import/export adapterは必要な境界として残します。第二の編集可能なrow正本は作りません。
- 名前編集機能はなく、次朝指標の意味も変更していません。探索全未来への重いUI viewコピーもありません。
- max／本人最適化／狩人GJ／一般の公開報告root／一般7～9人へのgroup拡張、生成前からの圧縮、root行ベクトルの輸送、既定有効化は残課題です。既存maxを均等に置換していません。
- **今回の9人winは未確認**。実施済みなのは3秒上限のroot対称性と通常生成診断（28配役・224状態・質量1・各対象1/8）のみ。9人の未来探索・完了性・高速化は主張しません。
- 既知の文言テスト失敗は未解決として残ります。今回の新規regressionと区別します。

公開push/deploy、共有設定・権限変更、無関係な最適化追加はありません。