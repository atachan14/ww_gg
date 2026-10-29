# Player view：UI読取切替

基準は `8d415cd`、数理は公開03e4e31のままです。公開の通常画面・table preview・roles先行/完了のtemplate行を `PlayerData` から読み取るよう接続しました。公開indexも `player_view` と各行のdeclarations／received_claimsとして同じ描画contextへ渡します。COは有効ログのcurrent_coとの一致を検査します。新しい被申告列や補足表示は増やしていません。

本人APIは、検証・計算済みの行を本人view経由で読み、既存のdict JSONへ戻します。公開の表を再計算するためではなく、既に所有しているBoardDataから最小限の公開メタデータを参照します。理由・取得履歴・budget診断など上位応答はそのままです。役職支持が未計算でplayersが空の場合も、従来のPending応答を保ち、架空の行を作りません。

フレームはroles／complete／Pending／不整合を区別します。本人の予算Pendingも保持します。名前は既存値、次の朝までの指標も既存値です。新しい名前編集、独立確率化、数理最適化、保存schema変更はありません。appの既存行組立はまだ残しており、その読取側を切り替えた小段階です。

## 最終コードの検証

- 関連120テスト成功、37.822秒。Player view、UI新旧比較、Board/所有履歴/訂正取消、cache、公開/本人stream、CO UI、private adapter/view、次朝指標等。
- 新旧読取を同じ入力で切替え、通常day/night、Pending、roles先行→completeのHTMLを完全比較。新経路で実際にPlayerDataが渡ることも検査。
- previewのrequest IDと未保存性、空の本人roles Pending応答、役職先行時の再構成回数、元cookie・公開入力不変を確認。
- 最終コードを専用18801で再起動し、実HTTPと独立headless Edgeで操作検証。既存QAサーバーのPID・コマンド・18801 listener・計算子が空であることを確認して停止。8771/8772やユーザーChromeには触れていません。
- ブラウザでは初期7/15、実際のroles→complete、計算中にCOを再編集し旧preview排除、入力更新→reloadで保持、本人狼→公開の復元、遅延本人応答の排除が成功。pageerrorは0件。
- templates／JSを変更せず、既存のBoard ID／revision／request世代照合と操作制御を維持しました。browser試験の待機selectorと期待値は既存仕様に合わせて修正しており、UI仕様変更でテストを通していません。

[機械可読結果](../benchmarks/player_view_refactor/ui-read-checks.json)。ログとday/nightの画面は `.artifacts/player-view-ui/`。操作driverは `benchmarks/player_view_refactor/check_ui.cjs`。これは18801を起動するものではなく、所有確認済みのローカルappサーバーで隔離した新規テストゲームを操作します。

## 残っている段階

旧行dictの組立・内部adapter撤去、逆引きの新しい表示設計、一致groupの通常計算接続はまだ行っていません。viewは現在の描画Board／視点／計算段階で作り、探索中の全未来Boardへ保存・コピーしません。既存保存形式と正本ログは維持します。全suiteの再実行ではなく上記関連回帰であり、既知の予算文言テスト失敗を解消したという報告ではありません。公開push/deployなしです。