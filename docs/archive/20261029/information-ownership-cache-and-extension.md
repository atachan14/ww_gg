# 情報所有・キャッシュ・拡張手順の独立整理

2026-10-13、基準9c89ba1。夜の全体対象比較は回答待ちで、UI切替は行わない。今回はその定義に依存しない公開prior共有と、役視点の公開方針再利用を実装した。

## 情報の所有と再利用

| 情報 | 実装 | 所有/再利用の条件 |
|---|---|---|
| 公開証拠 | appのpublic replay、public_prior.public_history_key | 公開CO/結果/取得日/公開日だけ。viewer/secret draftはkeyへ入れない |
| 公開取得prior | public_prior.prepare_public_prior | 全体・占い・狼で共有。Board、Rules、取得追跡mode、公開履歴、予算でkeyを分ける |
| 公開期待値 | model_a_public.evaluate_public_game | Board/Rules/Strategy/公開履歴/上限で分離。16件のimmutable完成結果。FuturePendingは保存しない |
| 役本人の証拠 | private_view.PrivateView、private draft store | Board/本人/役で独立。公開への初回コピー後はデータを共有しない |
| 狼の仲間 | condition_privateの初期狼mask | 死亡済み仲間も含む本人側情報。公開priorへ渡さない |
| 公開方針cache | InformationSetForecast.scores/policies | 公開Board/共同prior/公開履歴、狼の場合はその行動者の仲間mask。閲覧者条件をkey/rankingに入れない |
| 私的payoff cache | InformationSetForecast.values | 上記に加え私的共同priorとobserverそのもの。要求内だけで保持し、公開cacheへ昇格しない |
| 取得/観測 | acquire_laws、NightFrame | 公開と私的の生成を分離。observerは私的側だけ。物理死亡と公開観測更新の方針も分離 |

旧コードはvaluesのkeyでobserverの有無だけを区別していた。別engineだったため既存の占い比較では混同しなかったが、複数対象でengineを再利用すると異なる条件が衝突する。observerをkeyに含め、占いtargetをcallbackのdefault引数で固定した。ひとつのengineでtarget2の5/6とtarget4の23/30を両方返し、同じ公開方針が不変であることを回帰した。

seer_forecastは要求内のengineを共有し、3対象の同じ公開仲間方針を3回から1回の計算へ減らした。対象ごとのwork上限と要求全体の時間deadlineは従来どおり。異なる対象の私的値を使い回さない。実装上のobserverはhash可能で、評価中に意味を変更しないpredicateとする。

## 失効と古い応答

- 公開Board編集/戻る/進行：Boardの証拠・履歴・生存者・phaseが変わればprior/値のkeyが変わる。数値的に同じ公開snapshotなら別Board IDでも公開値を再利用できる。秘密は別IDのstoreへ移らない。
- Strategy変更：公開priorを変えない設定はpriorを共有し、期待値のStrategy keyを変更する。開示により取得追跡modeが変わる場合はpriorも別。
- 公開取得/公開日変更：public_history_keyが変わり、取得と公開の時点を取り違えてcacheを再利用しない。ログのowner表示だけは計算入力でないためkeyへ入れない。
- 秘密入力/本人/役/能力先変更：要求内の私的prior/observerを変更。公開policy cacheには秘密を混ぜず、公開cookie/logも変更しない。
- revisionだけの変更：計算keyとは別にAPIのboard_id/revisionが応答採用を制御する。app.private_viewが現在ID/revision以外を拒否し、JS controllerがrequest version/AbortControllerで古い応答を破棄する。数値cacheをhitしてもこの確認を迂回しない。
- 計算失敗：prior/公開値ともFuturePendingをcacheしない。途中までできた対象表を完成表として返さない。要求内の完成済み部分cacheは数学的に同じ入力でのみ再利用する。

開発用リセットはmodel_a_public.clear_public_cacheとpublic_prior.clear_public_prior_cache。公開/秘密の入力変更を一律cache clearで処理するのではなく、immutable keyで区別する。私的engineは要求終了で破棄する。

## 役職の追加手順

1. 情報所有者、取得時点、結果が死亡に影響するか、公開法を先に決める。公開申告と真の取得を同じ履歴にしない。
2. 役職状態/取得生成を追加しacquire_lawsへ接続。死亡に影響する能力はterminal_preflight_safe=Falseとし、NightFrame.afterを読むresolverを用意する。Boardの死体なし/複数死体/GJ規則はまだ未定義なので先に仕様決定する。
3. 公開観測・朝報告の生成法を追加。action_flow.resolve_actionとreport_flow/continuation_valueを使い、最終評価と期限内評価へ別の夜solverを複製しない。
4. 方針が読む情報だけで候補を比較する。私的条件を公開ランキングに渡さない。新能力が情報や死亡を変えるならexchangeable高速化の適用条件を狭める。
5. prior/cacheの依存入力を追加し、私的入力が公開keyに入らないこと、分布保存、時系列、同率/置換、部分失敗、revision/戻るを回帰する。

登録だけで新役職が動く仕組みや、狩人/GJそのものは今回追加していない。

## 共通化再監査の判断基準

- 同じ情報入力と同じ確率法で、更新順序や式が重複しているなら共有候補。具体的な呼出し2箇所以上と対応する回帰を示し、差し込み位置を減らす。
- 同じ形の式でも公開measureと私的measure、行動と観測、取得と公開は同一視しない。共有する機械処理には、その方針を明示的に渡す。
- 高速経路は適用条件と一般経路との一致を証明/回帰して残す。旧数値が速いだけではAへ流用しない。
- 新しい抽象化に現在の利用者や重複削減がない場合は先送り。全関数を一つにすることを完了条件にしない。
- 変更後に参照検索、既存対応、予算、情報所有を再確認。偶発的重複が残れば小さく直して再監査。モデル/仕様の判断が必要になったらそこで区切る。

今回除いた重複は、公開入力抽出、占い/狼/全体の取得prior準備、占い各対象の公開方針再計算。残る旧評価器は全体画面から使われているため、夜定義確定後の移行と参照移管までは削除しない。整理6項目と再監査の全完了はまだ宣言しない。

## 検証

全体413テスト、70.307秒、失敗/エラー0。公開prior所有/cache4テスト、既存秘密非漏洩/同率/置換/7/8対5/6を維持。占い視点7テスト1.773秒成功（直前2.056秒、厳密な性能比較ではない）。build/静的ミラー/diffチェック、DOM3種類、最新コードの実Edge3種類も成功。秘密訂正、公開不変、再選択、古い応答排除、reload/revision、昼夜/戻る、死亡済み狼、狩人未対応、狼同率、占い5/6・0/1・混合狼数1/2・生存狼2の1/3を確認。タイムアウトなし。

その後、[夜UIの切り分け](night-ui-current-and-migration.md)に対応するフラグ回帰1テストを追加し単独成功。アプリの追加変更はしていない。確認 http://127.0.0.1:8772 。ローカル保存のみ、push/deployなし。

## 混合能力の共有化更新

[mixed-model-a-optimization.md](mixed-model-a-optimization.md) の公開朝/報告cache、observer識別子付き行動cache、単独偽の公開ノイズ積分、取得履歴付き置換キーを追加。policy自体は置換キーへ保存しない。登録能力が死亡・情報・行動へ影響する場合は、`evaluation_projection`、`joint_value_key`、`informative_seer`、スカラー絶対境界を再審査する。
