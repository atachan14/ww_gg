# 6人入力訂正registryと要求時の個人枝復元（独立試作）

`SixInputRegistry` は明示した6人・狼1・占い1・狩人0・霊0/1の保存入力から作る。初日/二日目の昼snapshotに限定し、既存の公開log transaction、owned change commit、BoardData.updated、SavedOriginを使用する。現在の事後分布を入力とせず、訂正後の有効入力と元の配役・ルール・方針・観測履歴から再構築する。通常UI・共通ルール・公開設定・サーバーは変更していない。

初期 `SavedCutOutGraph` の6人 `corrected/bind` も接続した。途中registryでは `edited(payload)` が現在所有元の既存transaction、`corrected_root(base, reports, medium_reports)` が初日所有元の明示的な入力訂正。後者は構成済みの同じ行動履歴を再生する試作APIで、実アプリのBoard切替/全archive管理との統合ではない。

## 訂正と保証

初日CO取消→再入力、二日目の結果変更→取消→再入力、二日目に行ったCOと過去取得結果の公開→取消→再入力を確認した。旧snapshotの入力・共同分布は不変で、GameData/runtimeを共有した新snapshotが別revision/digestを持つ。旧Tableはstaleになる。候補を一律追加せず、初期/物理生成から再構築して支持を復活させる。

二日目COの取消では元の無CO共同分布へ、再入力では直前のCO後の共同分布へ、公開/物理の両方が厳密に戻る。P1の公開狼率は初日COなら1/4、二日目COなら5/8となり、現在COから初期priorを作り直す誤りを避けている。初日訂正での無CO初期支持は30配役×合法白4通り＝120状態、二日目無COの秘密履歴は272状態を保持した。

公開Q、本人のQ条件付け、実際の物理Pを別々に保持する。結果訂正で支持を失った旧wolf-roster枝は `InvalidatedBranch` となり、結果を戻すと同じ完全共同分布を再構築できる。実際の物理経路の枝massはPから計算し、公開役職率へ置換しない。試験例の個別actor枝massは1/38。

生成requestは、行動と観測・今回追加された朝報告・本人役職/取得・狼rosterという意味descriptorへ登録する。旧hypothesis対応表は転用しない。古い報告prefixも追加公開recipeへ埋め込まない。共通cacheが使う公開信念へのbridgeは実際の物理経路ではないため、独立した物理枝massを返さず、訂正後はsnapshot-localとして破棄・新評価から再発行する。公開/物理のsource_kindを保持して両者を混ぜない。

## 画面が必要とする復元

既存画面は app.py:276–309 で主要値・累積値・行動/翌朝値と現在のPlayerData全行を組み立てる。個人APIは private_adapter.py:61 と player_view.private_api_rows を使用する。ここでは全終端木の配列を要求していない。

`current_screen` は同じValues形式・既存formatterで主要/累積値と全6行を返す。公開/本人の完全共同分布と物理共同分布も保持し、個人間相関は完全法則の厳密な和で読める。表示結果を周辺率だけに置換したり、個人別の相関を落としたりしない。通常テンプレートへは接続していない。

`preview_action` は要求された生存者ラベルと観測をdescriptorにし、`LazyBinding.read` で初めてその枝を共通ActionEvidenceから再構築する。代表と同じ勝率だけで済ませず、その個人ラベルの完全な公開/本人法則・物理Board・履歴・massを返す。選ばれなかった全終端木のラベル復元は検証・全枝解析用であり、現在Tableや一つの個人枝の表示には実行しない。将来、全木が必要な用途には依然として追加費用が必要。

## 有限試験と画面相当の費用

再現: `python -B -m benchmarks.player_match_groups.cut_out_six_registry_fixture`。各run60秒、全体300秒、Windows WorkingSet 1,500,000,000 bytesで停止。今回の有限計測は計 9.907 秒、peak最大 37.8MiB。重いworker・全suiteは実行していない。新規6本＋既存17本＝23回帰テスト成功、ログは `.artifacts/test-cut-out-six-registry-final.log`。

新規プロセス3反復では、起動/import→保存snapshot準備→Forecast→主要/累積値と完全Tableまで 0.408–0.420秒。一つの個人枝の完全joint読戻しまで 0.411–0.423秒。Table生成を含む現在表示処理は約 0.098秒、個人枝の追加費用は約 0.0036秒、本人Table要求は約 0.045秒だった。HTTP通信・実HTMLテンプレート描画・実サーバー起動を含む測定ではない。予測結果の一般的な速度保証ではない。

全個人Forecast、coldなSavedOrigin、純粋な既存action/project処理と、完全Table・主要/累積値・行動/翌朝/勝率・公開/本人/物理joint・相関・枝massが一致。訂正後の群内swap不変性もテスト側で監査し、実行時の置換探索には使わない。霊COの報告保持と本人情報に他人の取得を渡せないことも確認した。

## 未解決の既存仕様

**初日のCO・報告を、後日のBoardからまとめてwithdrawする経路は未対応。** 有効logでは全CO/報告が消える一方、`result_disclosure.snapshot` が過去prefixで後日のwithdrawを除いて旧COを復活させ、root再生のpastは有効報告を持たない。旧正式SavedOriginでも `full_disclosure_truth_not_conditioned` になる。診断は `...cut_out_six_registry_fixture blocked` で再現する。

この編集後の候補入力は保持し、評価/recipeは明示的なInvalidated/Pending状態とする。旧snapshotは変更せず、withdraw batchの削除で共同分布が厳密に戻る。旧fake報告を本当の秘密取得として足す補完や、均等化・省略による救済は行わない。承認拒否ではなく共通仕様の未対応であり、今回の通常/公開変更なしの範囲では共通意味を変更しなかった。所有元が二日目のCO取消と、初日所有元の訂正は上記のとおり成功。

夜snapshotでの入力編集、任意の所有元切替/実UI archive統合、latent私有条件を含むすべてのcache projection descriptorの永続再利用、全終端木の効率的復元、7人・max・狩人は未対応。証拠は `cut-out-six-registry-results.json`。途中COのすべての撤回形態が完成したとは扱わない。

このPendingの最小再現と、旧oracleを変えない明示フラグ修正の診断は[次段階の記録](withdraw-prefix-diagnostic.md)を参照。標準入口は未切替。
