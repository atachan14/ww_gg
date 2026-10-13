# 構造整理の仕上げ（2026-10-13）

基準48d8813。数値仕様、新役職、公開版は変更しない。

## 今回共有した部分

morning_flow.report_flowが「霊能報告の各結果→共同分布の射影→占い公開→次の公開Board/取得状態/履歴」を生成する。continuation_valueが渡された枝の重みで次評価を加算する。旧公開占い評価とモデルAの朝報告/霊能候補評価で共有する。生成は遅延し、旧計算の生成・予算チェック・再帰評価の順序を維持する。

旧公開PublicMorningPolicyは、既知偽占い一人のノイズ周辺化と従来の取得履歴周辺化を保持。モデルAはInformationSetForecast.publications/project、pushによる私的重み付けを保持。霊能randomの枝混合、maxの選択は統合しない。旧公開は候補の最小値、Aは公開入力で比較した同率最適指示を均等混合する。違いをcommon flowへ隠さない。

## 役職追加時に実装する部品

| 部品 | 現在の例・追加先 |
|---|---|
| 状態・取得履歴 | exact.Board、seer_acquisition.Hypothesis/Acquisition、seer_future_uniform.TrueScanState。新役職の情報所有者・取得時点を定義 |
| 夜の能力結果生成 | seer_future_uniform.acquire_uniform。各ActionPolicy.acquireから結果生成を接続。共通action_flowの夜/昼・終局・後続分岐を複製しない |
| 死亡/終局と観測 | exact.action_outcomes、phase_updatesの観測更新。規則と戦略選好を区別 |
| 公開結果生成 | morning_publications.future_publications/public_report_branches。各MorningPolicyの生成法へ接続し、report_flowの射影→公開→後続の配線を複製しない |
| 行動選択/情報の範囲 | 公開PublicActionPolicy/PublicMorningPolicyとAのInformationSetActionPolicy/wolf_policy/day_scores。私的情報の所有範囲が違うので両方の契約を確認 |
| 私的入力と画面 | private_view.condition_private、private_adapter、board_private_draft/row/table。公開ログ・公開フォームと秘密保存を共有しない |

例：別の能力の夜結果を朝に公開する場合、結果履歴と生成法、公開法、必要な情報条件を実装する。夜判定、死亡後に朝へ進む分岐、朝の枝確率掛け合わせ、次評価の加算を二つのsolverへコピーする必要はなくなった。ただし役職登録だけで自動対応する仕組みは未完成であり、将来COや役騙りも未実装。

## ループの数と残す理由

共有する進行機械はaction_flowの対象行動→取得→死亡後→朝/昼継続と、report_flow/continuation_valueの報告→次評価の2つ。

本番の主な最終勝率再帰は4系統：exact.solve（狼数/位置の圧縮）、reports.solve_reports（霊能共同分布の圧縮）、seer_future_forecast.forecast内solve（従来公開占い）、InformationSetForecast.solve（公開判断と私的重みを分離するA）。Aには無情報の対称盤面用exchangeable_valueという補助再帰も残す。旧wolf_view_forecastは本番APIから未使用だが参照テストがあるため残す。

最初の2系統は性能のための圧縮計算、後ろ2系統は情報集合・更新・周辺化の仕様差がある。削除や一本化には性能/モデル変更の検証が必要なので、この整理ではここで止める。

## BoardOverviewと視点評価の差の所在

app.render_main→seer_future_bridge.evaluate_game→従来forecast/圧縮exactがBoardOverview。private_adapter→information_forecastが役視点。入口の切替は明示的に残す。

従来PublicActionPolicy.outcomesは公開分布上の指定行動を使う。InformationSetActionPolicy.outcomesは仲間/閲覧者側の物理枝と、死体整合性だけの公開更新を分ける。Aのwolf_policyは仲間ごとに未知役職を平均してからmax、day_scoresは公開入力だけを使う。公開生成の周辺化差はPublicMorningPolicy、Aの私的重みはpushに閉じ込める。共通flowがこれらを選択しない。

同じ白を報告した占いCO2人の片方を処刑する5人例で、BoardOverviewの7/8とAの5/6を維持。差を揃えることは将来のモデル変更として別途判断する。

## 護衛/GJに向けた契約と不足点（設計のみ）

現在のaction_flow.acquireは死亡前Boardを受け取る。public/observerの取得状態は別々に保持し、終局では公開せず、生存者だけ朝報告へ進む。占い取得は死亡の成立法を変えないため、旧計算の終局時取得省略を保つための先行死亡候補列挙を許す。

護衛は取得結果/防御先を死亡生成へ渡す必要がある。現在outcomesは取得前payloadを受け取るので、そのまま護衛を追加してはならない。必要な拡張は「行動・夜能力の決定→防御を含む物理死亡結果→公開観測」の契約、GJ/死体なし/複数死体の観測枝、能力/観測の情報所有者と相関、終局判定の位置、夜取得省略条件。生存者数だけから偽のGJ値を作らず、仕様決定後に回帰とともに導入する。

## 実測検証と保存

- 全体396テスト、75.406秒、失敗/エラー0。モデルA専用8テストも5.745秒で成功。7/8対5/6、同率、プレイヤー置換、秘密を公開判断へ混ぜない回帰を維持。
- 新しい朝flow3テストで枝確率の合成、公開履歴引継ぎ、遅延生成と再帰評価の順序、私的重みの維持、途中失敗で数値を返さないことを確認。
- DOM3種類、build_vercel.py、静的ミラー回帰、diff --check成功。
- 全体終了後の実Edgeで秘密再計算/訂正、公開不変、再選択、古い応答排除、再読込/revision保持、昼夜/戻る、狩人未対応、死亡済み狼、狼同率比較成功。占い5/6・0/1・不確定狼数1/2・生存狼2の1/3も単独実行で成功。
- 最初の占いEdgeは選択後の30秒待機を超過した。その実行ではprivate-view POSTがサーバーに届かず、計算予算超過の証拠はない。単独再実行は成功。画面選択/待機の一時的失敗として記録し、原因確定や計算タイムアウトと扱わない。時間制限は変更していない。
- 確認URL http://127.0.0.1:8772 。ローカル保存のみ。Gドライブ、master、push/deploy、新能力は変更しない。
