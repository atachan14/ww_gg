# Vercel 試験公開の確認

公開先: https://ww-gg.vercel.app/

## 公開コードと状態

- GitHub `atachan14/ww_gg` master: `48d294f257e3cc8ec6022e27fcf0fae77e7ce411`。
- Vercel `ww-gg`、Hobby、最新ProductionはReady。Deployments一覧のSourceと完全SHAの表示を照合。
- 自動再ビルドのdeployment: `ww-9lzf1n7nh-aklius14pg-8355s-projects.vercel.app`。
- 署名キーはユーザー本人が生成・入力・Deploy。こちらは値・clipboard・認証cookieを取得せず、再保存・自動pushもしない。

初回のprojectメタデータ不足はb436c2cで、静的404は48d294fで解消。Readyだけで完成とは判断せず、配信と操作を別に検証しました。

## 配信と限定HTTP確認

[HTTP記録](vercel-public-http-checks.json)。TOPは200。CSS、app.js、strategy.js、parallel.js、comparison.jsの5資産すべて200。公開資産のSHA-256は送信済みGit blobの内容と完全一致。Windows作業コピーのCRLFではなくGit保存内容と比較しています。

自分専用の新規cookieセッションで3〜9人の素村＋狼代表初期盤面を確認。start POSTからMAIN GETへのリダイレクトを含む応答時間は0.430〜0.681秒、すべて200。人数3/4は狼1、5〜9は狼2。期待村勝率は順に1/3、1/4、2/15、1/12、8/35、5/32、94/315。HTTPS用cookieのSecure/HttpOnly属性と継続を確認。cookieの値は記録していません。

これは限定代表リクエストの実測であり、cold startや全配役・全履歴のクラウド上限、同時アクセス耐性の保証ではありません。全履歴のローカル検証は既存の版別記録・[リクエスト計測](vercel-request-benchmark.json)を参照。

## 公開ブラウザQA

通常Chromeのログインは管理画面確認だけに使用。公開QAは専用の独立Edge headlessプロファイルと自分のセッションで実施し、ユーザーの画面・認証プロファイルを使いません。終了後に当QAブラウザを閉じました。

[ブラウザ記録](vercel-public-browser-checks.json)。PC1100×1000、mobile390×900のエミュレーションを確認。

- TOP→MAIN、既定5人の7/15。
- ％→分数切替、Game/Board設定とテーブル幅。
- 昼max→random→maxの即時反映。進行せず保存されること。
- 5人・霊能1のCO変更とItem取消。
- 昼の進むを連打しても1回だけ夜へ進行。
- 夜→翌日昼、霊結果「白」の即時反映と再読込後の保持。
- 戻るで前Phaseと対象Player3が復元。
- 9人 C3/M2/S1/H1/W2、Player1霊能COの94/315。
- PCの数値・設定・テーブルに横はみ出しなし。mobileの縦配置と固定フッターの進行ボタン。
- 記録した公開ページの52応答に4xx/5xxなし、ブラウザ例外なし。

スクリーンショットは作業フォルダの `vercel-public-main.png` と `vercel-public-mobile.png`。実端末のtouch操作や全mobile環境、全配役を網羅した公開試験は今回の範囲外です。

## 結果

試験公開と依頼された代表QAは完了。公開コードは48d294fです。この確認記録の追加はローカル文書のみで、再push・再Deployはしていません。README改修の依頼は別件の読取調査に留め、READMEを編集・削除していません。
