# Vercel 試験公開の準備

基準 UI コミット: `cbd0eac`。この記録は公開前の準備であり、デプロイ成功の記録ではありません。

## 既存接続の読み取り確認

ユーザーPCで既に開いていた Chrome（PID 7040、既存通常プロファイル）を使用。隔離 Edge のログインをユーザーのログインと扱っていません。Vercel dashboard と新規インポート画面の可視テキストのみ確認し、cookie・token・認証ファイルは取得していません。

- ログイン表示: `aklius14pg-8355`。
- 現在の Vercel Team: `aklius14pg-8355's projects`、Hobby。
- GitHub 接続済みインポート一覧に `ww_gg` が存在。
- 選択後の表示: `atachan14/ww_gg`、`master`。ローカル remote `ww_gg` の送信先とも一致。
- 新規 Project Name の候補: `ww-gg`。プロジェクトはまだ作成していません。
- 初期 Root Directory 候補が `archive/python-legacy`、Preset が FastAPI。公開時に **リポジトリ直下 `.` と Flask** へ修正が必要。
- Import は設定前画面への遷移だけ実行。Deploy、新 OAuth、課金変更、MCP 認証変更、CLI 導入は行っていません。Niixy の設定・権限は変更していません。

## 最小構成

- `wsgi.py`: Flask インスタンス `app` を公開用設定で作成。
- `pyproject.toml`: `wsgi:app` と静的ビルドコマンドを明示。
- `.python-version`: Python 3.12。依存は既存 `requirements.txt` の Flask 3.1.2。
- `build_vercel.py`: first-party CSS/JS をビルド時に `public/static/` へコピー。既存 `/static/...` URL を維持して CDN 配信。初回公開確認後の修正で、配信する5ファイルのミラーをgitにも含めています（下記参照）。
- `.vercelignore` と function の `excludeFiles`: archive、UIサンプル、docs、tests、ローカル環境、`.env` 等を配信・関数bundleから除外。templates と werewolf は維持。
- `vercel.json`: Flask と `wsgi.py`、単一関数の上限60秒を明示。DB・近似・計算エンジンの変更はなし。

現行公式資料: [Flask](https://vercel.com/docs/frameworks/backend/flask)、[Python runtime](https://vercel.com/docs/functions/runtimes/python)、[Function limits](https://vercel.com/docs/functions/limitations)。公開用 entrypoint、`public/**`、Python 指定、excludeFiles を資料と照合。Hobby の現行上限は300秒・2GBですが、当構成は60秒を指定します。ローカル実測からクラウドの処理時間や同時アクセス耐性を保証しません。

## 署名キー契約とユーザーの手動手順

公開用は `WW_GG_SECRET_KEY` に **64桁の16進文字列（32バイトの安全な乱数）** を要求し、未設定・不正形式なら起動を停止。公開環境で起動ごとの乱数へフォールバックしません。cookie は Secure / HttpOnly / SameSite=Lax。複数インスタンスで同一キーを使う検証を実施しています。

秘密値の生成・既存値取得・チャット出力・入力は今回実施していません。以下はユーザーが行う手順です。

1. パスワード管理ツール等の安全な乱数生成機能で、上記形式のキーを生成し安全に保管。チャット・repo・コマンドログへ貼り付けない。
2. 正しい `ww-gg` 新規設定画面で Root Directory を `.`、Preset を Flask にする。既存サービスのプロジェクトは編集しない。
3. Environment Variables に名前 `WW_GG_SECRET_KEY` を追加。値はユーザーが直接入力し、利用可能なら Sensitive に設定。Production と試験用 Preview の適用範囲を確認する。同じ対象環境のインスタンス間では同一値を維持。
4. 準備コミットを GitHub `atachan14/ww_gg` の `master` に送信した後、そのコミットを選んで Deploy。自動ビルド設定の上書きは不要。勝手な有料アップグレードはしない。
5. 公開 URL で TOP、静的4ファイル、3〜9人の代表盤面、表示切替・進行・戻るを確認。署名キーや cookie 値を検証ログに出さない。

キーを後から変更すると既存 cookie が無効になります。cookie の内容は署名されますが暗号化されません。実役職配置や秘密認証情報は session に追加していません。ローカル起動は従来の一時キーと loopback のままです。

## 入力・容量の狭い点検

- 本文4096バイト、フォームメモリ4096バイト・multipart100部を上限とする。
- 未知・重複フィールド、3〜9人と人数制約、既存 revision・対象・CO・霊能報告検証を維持。
- cookie 署名改ざんは盤面として受理しない。
- 保存予定 cookie ヘッダーが4093バイトを超える更新は400として拒否し、以前の cookie を保持。値自体はログに出さない。
- Origin 不一致または `Sec-Fetch-Site: cross-site` の POST を403として拒否。同一Originのフォームを確認。
- 公開ベンチマークAPIや任意人数入力は追加していない。既存の有界キャッシュ、厳密評価を維持。

## 検証と未完了

追加6件を含む unit test **92件合格**。未設定キーの失敗、別インスタンス間の署名継続、改ざん拒否、cookie上限での旧状態保持、本文上限・外部POST・重複入力、CDN用4資産のコピー内容を確認。

[単一リクエスト計測](vercel-request-benchmark.json) は `python -B tests/benchmark_requests.py --output docs/vercel-request-benchmark.json` で再現。Flask test client の各リクエストを個別に冷キャッシュで計測し、3〜9人と9人の役職・CO代表盤面を終局まで進める。tracemalloc は Python の割当ピークであり process RSS ではありません。第一夜だけの速度を完成根拠にしません。

Vercel自身での build・CDN配信・実際の cold start・同時アクセス・公開後の cookie 継続は未確認。正しいルート/Presetの選択、ユーザーによるキー設定、GitHub push、Deploy は残っています。キー欠落のまま公開成功を主張しません。

［判定］は [UI確認記録](right-parallel-checks.md) と一致し、**処刑／噛み直後に勝敗判定する** 固定説明です。可変パラメータではありません。

### 今回のローカル計測結果

3〜9人の素村＋狼代表例は1〜7 Phaseを終局まで進行。最大単一リクエスト0.349秒、最大 cookie ヘッダー483バイト。9人 C3/M2/S1/H1/W2・霊能CO2名・CCOなし代表例も7 Phaseを終局まで進行し、最大単一リクエスト11.510秒、Python割当ピーク10.844MiB、最大 cookie ヘッダー499バイト。全例の最大応答本文25,109バイト。公開用のSecure属性ではcookieに7バイト追加されます。いずれも代表例の実測であり、全配役・全入力の最悪上限ではありません。

## 初回Vercelビルド失敗と修正

ユーザー本人がキーを貼付してDeployを実行した後、Vercelの依存解決で失敗。可視Build Logsの原因は `error: No project table found in: /vercel/path0/pyproject.toml`。署名キーの検証前の失敗であり、キー内容は取得していません。

`pyproject.toml` に `[project]`、名前 `ww-gg`、version、Python `>=3.12,<3.13`、依存 `Flask==3.1.2` を追加。Vercelのuv依存解決が扱えるproject構成に合わせました。依存定義と従来requirementsの一致、entrypointと静的ビルド契約を回帰テストに追加。

ローカルにuvはなく追加導入は行っていないため、Vercel自身のuv lock・build成功は修正コミット送信後に確認する必要があります。秘密値の再入力・保存確定は行っていません。


## b436c2c の公開確認と静的配信修正

Vercel は Ready、Source は b436c2c。GitHub master の完全SHAは `b436c2c17565da67d58d0d87e246ef67482e44d4` と一致。公開先 https://ww-gg.vercel.app/ 。TOP は200、CSS/JS4ファイルはすべて404だったため、Readyを画面完成とは扱っていません。

実ログ: Vercel CLI62.1.0、Python3.12、uv0.10.11、`Executing: python build_vercel.py`、Build Completed。コピーコマンド未実行ではありません。[現行公開builderソース](https://raw.githubusercontent.com/vercel/vercel/main/packages/python/src/index.ts)はPython関数からpublicを除き、通常Flaskのpublic CDN収集は別処理です。ビルドhookで後から作ったpublicファイルが初期静的出力に入らなかったと推定しています。

対処は、first-party CSS/JS5ファイル（主画面4＋比較画面1）だけを `public/static/` にミラーしgitに含め、ビルド開始時から配信資産を存在させること。元の `static/` はローカル配信と編集元として維持。既存build hookもミラーを更新します。回帰テストで5ファイルの完全一致と余計なファイルがないことを検査します。publicへの秘密値、archive、UIサンプルのコピーはありません。Vercel本体上での404解消は新しいコミットの手動push後に再確認が必要です。

公開側の限定HTTP確認: 自分専用の新規cookieセッションで3〜9人の素村＋狼代表初期盤面がすべて200。startからMAINへのリダイレクトを含む実時間は0.413〜0.479秒。Secure/HttpOnlyの署名cookieが継続しました。静的404のため、公開ブラウザでのCO・戦略・霊能更新・進行・戻るとmobile QAは未完了。公開負荷試験や全履歴性能保証ではありません。

共有Chromeはユーザーの通常プロファイルをWindows UI Automationと必要時の前面mouse/keyで操作。公開HTTP確認は背景で実施。管理画面の認証cookieは抽出・複製していません。今後の公開ページQAは、認証不要の独立Edgeプロファイルで分離可能です。認証を伴う管理操作を完全に分離するには、ユーザー自身がログインする専用VM等の別デスクトップが候補ですが、今回は新環境を構築していません。

静的ファイルを編集した後は `python build_vercel.py` で `public/static/` を同期し、テストで編集元との一致を確認してからコミットしてください。


## 静的配信修正後の公開確認

48d294fの手動push後、ProductionのReady/Source完全SHA、5資産の200とGit blob完全一致、限定3〜9人HTTP、隔離EdgeのCO・戦略・霊結果・進行／戻る・PC/mobile代表QAを確認。結果は [公開確認記録](vercel-public-checks.md) を参照。秘密値の取得・再保存、自動pushは行っていません。
