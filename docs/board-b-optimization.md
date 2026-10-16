# B実装の性能改善

評価コミット `3c11498` を保持した追加変更。B1→B2→3a→3b と生成Boardの証拠再構築は維持する。

## Gameの寿命と再利用

既存アプリでは共通配役・GameRulesは `/start` で新しいGameを作るときだけ変更され、既存の `co_display_game` 識別子もそこで更新される。この識別子に対応するGameRuntimeが共通情報と完了結果を所有する。BoardごとにRuleをコピー・値比較しない。架空の設定世代も追加しない。

公開結果のキーはBoard入力と計算予算。本人結果には役職・本人位置・秘密結果も含む。履歴、公開報告、方針はBoard入力に含まれる。新しいGameは別Runtimeを持ち、以前のGameを破棄する。Game最大16件、各Gameの完了結果最大32件のLRU。本人Tableは保存・取得時にコピーする。Pending、部分的な公開結果、必要な本人値が未計算の結果は保存しない。参照計算モードでは完了結果の再利用も無効にする。

キャッシュが当たっても3aの表示用役職分布は通常どおり再構築する。GameRuntimeを明示しない独立した `BoardData.from_game` は独立Gameとして扱う。

## coldでの重複削減

秘密仮説の質量を除く比較キーを、正規化済みの不変Hypothesisから直接作る。質量を1に置換するためだけのHypothesis生成を削減し、同じ質量なら既存仮説を使う。型・全比較フィールドを維持し、派生型や互換入力は従来の検証経路を通す。公開重み、世界内秘密混合、物理枝質量の意味は変えない。

## 検証状況

途中版は全670テスト成功（418.320秒）。最新追加12テスト成功（0.563秒）。最新全テスト、正式三者比較、ブラウザ検証は続行中。これらを完了するまで速度改善を測定済みとは扱わない。

Morishiとの重複を避け、こちらのテストを20:09 UTCに停止した。Morishiの重い処理は20:15:15 UTCに終了との連絡後に最新全テストを再開。重複時間帯の実測値を主たる性能証拠には使わない。

最新全体実行: 671件405.462秒、670成功・7人observed HTTP予算テスト1失敗。変更なしの同一テスト単独再実行は18.533秒で成功。全体実行の失敗は隠さず残す。速度・予算余裕は正式比較とブラウザで別途確認する。

## 正式三者比較

改修コードは `1609d2f`、旧版は `ec513c2`、B改修前は `c6dd475` に固定。評価コミット `3c11498` と既存の評価結果は変更せず保存した。

同じ入力・予算で各ケース5反復。版とケースの順序を交互に反転し、新規プロセスでcold、そのプロセス内の同一Gameでwarmを計測。GameRuntime作成はGame作成の責務としてリクエスト計測の外。これはBoardごとのルール値比較ではない。テスト・ブラウザ要求を並行実行しなかった。時刻・CPU時間・背景負荷・全試行・実キャッシュ回数は `benchmarks/results/board_b_optimization_results.json` に保存。

中央値（秒）:

| ケース | 旧cold | B前cold | B後cold | 旧warm | B前warm | B後warm |
|---|---:|---:|---:|---:|---:|---:|
| 基本5人 | 0.000882 | 0.000841 | 0.000837 | 0.000466 | 0.000610 | 0.000443 |
| 保存7人・旧観測方式 | 11.161 | 15.144 | 14.877 | 0.001153 | 16.447 | 0.012207 |
| 保存7人・公開報告観測 | 10.905 | 14.627 | 14.324 | 0.001361 | 15.549 | 0.015750 |
| 本人占い履歴 | 0.022878 | 0.028590 | 0.028293 | 0.019821 | 0.028304 | 0.002011 |

全120要求が完了し、対応する役職分布・候補・合法手・勝率・同率選択分布は完全一致。7人のcold短縮はB前比約1.8%と2.1%にとどまり、旧版比はなお約33%と31%遅い。cold問題の解消とは評価しない。warmの大きな退行は改善したが、3aの再構築が残るため7人では旧版の約10～12倍の時間が残る。絶対値は約12～16ms。短いケースの背景負荷推定は量子化誤差も大きいため、微小なcold差を強い改善証拠にしない。

改善版の各ケース全5反復で、cold後はmiss1/store1/entry1、warm後はhit1。本人ケースも同様。単に既存の別キャッシュが温まった結果ではない。

## 正確性・入力分離監査

旧/B前/B後の各版で、15ケースの新規プロセス結果と29要求の混在順序を照合し、計132要求一致。入力、履歴、取消、日中/夜方針、ルール変更による新Game、本人位置、公開/本人往復、Pendingと部分Tableを含む。入力そのものの不変も確認。Game共通の変更ケースは新Game識別子を明示し、BoardのキーにRule値を入れていない。

共同分布監査4ケースも三者一致。公開配役と秘密履歴の共同分布、本人条件付き状態を比較した。すべての将来状態・情報集合での同率方針を列挙した証明ではない。未実装値は今回もPending/未計算のまま保持する。

再現コマンド:

```
python -B benchmarks/board_b_benchmark.py run --output .artifacts/b-benchmark/optimization-formal --repeats 5 --improved-ref 1609d2f
python -B benchmarks/board_b_cache_audit.py run --versions old,new,improved --snapshots .artifacts/b-benchmark/optimization-formal/snapshots --output .artifacts/b-benchmark/optimization-cache
python -B benchmarks/board_b_joint_audit.py run --versions old,new,improved --snapshots .artifacts/b-benchmark/optimization-formal/snapshots --output .artifacts/b-benchmark/optimization-joint
python -B benchmarks/board_b_optimization_report.py --baseline .artifacts/b-benchmark/optimization-formal/summary.json --cache .artifacts/b-benchmark/optimization-cache/summary.json --joint .artifacts/b-benchmark/optimization-joint/summary.json --output benchmarks/results/board_b_optimization_results.json
```

## HTTP・ブラウザ

専用18801の実行ファイルと対象パスを確認してPID24788へ再起動。PC1366px、狭幅390/320px、390pxダークでHTTP200、基本勝率7/15、進行、本人狼、公開表示不変、HELP、横溢れなし、JSエラーなし。本人占い履歴は村5/6・狼1/6を維持しセッション不変。保存7人の公開報告ケースはHTTP200、113/504、16.876秒、JSエラーなし。これは通常UI確認であり正式ベンチマークの中央値へ混ぜない。

新しいCO・報告規則やmax方針、GameTree機能は追加していない。未実装範囲を全対応と扱わない。

## 最終回帰と残件

同じ製品コード1609d2fで全体再確認も671件406.045秒、670成功・同じ7人observed HTTP予算テスト1失敗。最初の全体実行405.462秒の1失敗と再現した。単独テスト18.533秒、通常ブラウザ16.876秒、正式比較全120要求は成功しているが、全体実行の失敗を成功へ置き換えない。計算予算・期待値・max方針は変更していない。**全テスト成功の完了条件は未達**。残件は `tests.test_board_future.GeneratedBoardTests.test_saved_seven_player_observed_model_completes_the_http_request_budget` の全体実行中の安定完了。GC・直前計算の所有寿命などが原因かは未確定であり断定しない。

追加キャッシュ回帰12件成功、計測器回帰9件成功。評価結果・実装・監査は保存し、失敗ログも `.artifacts/integration-validation/b-game-cache-final-tests.log` と `b-game-cache-final-recheck.log` に保持。正式計測は約20:29:12～20:39:23 UTC。計測終了後にブラウザ確認、その後に全体再確認を実行した。次の調査で製品コードを変更した場合は今回の固定1609d2fの測定と混同せず再検証する。
