# ww_gg

人狼ゲームの盤面・公開情報と条件から、各行動・各Phaseの厳密な期待勝率を求めるツールを、要件から作り直す。

**公開Boardによるv0.4を反映済みです。** 市民・霊能・占い師・狩人・狼の3〜9人に対応します。霊能申告は手入力し、将来の報告機会は指定方策に従って厳密に分岐します。占い師・狩人は能力なし。CCOは複数条件を選べます。[Vercel試験公開](https://ww-gg.vercel.app/)の確認中です。静的配信の修正は[公開確認記録](docs/vercel-preparation.md)を参照。

仕様と検証は [v0.4](docs/v0.4.md)。昼は村勝率max、夜は狼勝率maxが既定、randomは候補等確率の期待値です。最大同率Actionは保持し、画面の初期対象は同率最小ID。手動変更は保持します。確率・勝率は％を標準にし、分数へ切り替えられます。

ローカル比較用の [2段階試案](docs/two-stage-prototype.md) を追加しています。TOP・MAINの「初期盤面の2段階比較」から開けます。正式採用ではなく、試案の共同分布・勝率は未定義です。

通常の新規ゲームは [COグループ方式](docs/co-group-model.md) が既定です。[戦略UI②](docs/strategy-ii-checks.md) の盤面評価で初日昼に全配役一様へ切り替えられます。進行後は固定し、既存Boardは保存モデルで継続します。全配役一様の内部計算・比較用API・数値回帰テストは保持しています。

## 現在の要件

正本は [docs/requirements.md](docs/requirements.md)。v0.2の複数狼・9人を維持し、配役人数、CO、騙り・CCO制約と役職別確率に、v0.4の霊能申告・将来開示を追加しています。

Tree可視化は後回し。内部の確率分岐の評価は初期対象に残す。MC推定を厳密期待値の代替にはしない。

## ローカルで確認する

Python 3.12とFlask 3.1.2を使用。現在の環境では既存のFlaskを利用し、依存追加は行っていません。

```powershell
python app.py --port 8771
```

[http://127.0.0.1:8771/](http://127.0.0.1:8771/) を開く。Windowsでは `start.cmd` でも起動できます。ループバックだけで待ち受け、既存 `.env` を読みません。DB・クラウドAPI・外部公開は使用しません。別サービスで使用中のポートは避けてください。

1. TOPで市民・霊能・占い師・狩人・狼の人数を入力し、計算条件と自噛みRuleを確認して初日昼へ進む。初期値は5人・狼1人、自噛み不許可。
2. MAINで候補別勝率を確認し、生存対象を1人指定する。情報欄の右で％／分数を切り替えられる。
3. 「夜に進む」「翌日の昼に進む」で、指定Actionの未決着Boardへ進む。全結果が終局なら決着画面へ進む。5人村では昼・夜・翌日昼の3行動を確認できる。
4. CO・計算条件の変更はその場で自動反映する。「再計算」で再試行できる。「前のBoardに戻る」は直前の対象と当時の戦略を復元し、そこからの進行を作り直す。

正本は初期配役・ルール・対象履歴と各行動時の戦略です。そこから公開Boardの生存者・Phase・相関付き役職候補分布を導出します。候補配置を内部計算で列挙しますが、本当の配役を1つ選んだり抽選したりしません。未決着の1w・2wなどを同じBoardに保持します。全候補の終局値をFractionで逆算し、同値な公開状態をキャッシュで共有します。現在Boardの条件付き勝率を主表示し、既終局枝も含めた「開始時点からの累積」を別表示します。この表示は調整可能な仮案です。表示切替は盤面や選択に影響しません。セッションはブラウザーcookieで保持し、サーバー再起動で初期化されます。

```powershell
python -m unittest discover -s tests -v
```

[この版の仕様・確認記録](docs/v0.4.md)、[9人実測](docs/v0.4-benchmark.json)、[v0.3記録](docs/v0.3.md)、[v0.4計画](docs/v0.4-plan.md)、[v0.2記録](docs/v0.2.md)、[v0.1の確認記録](docs/v0.1-board-checks.md)、[旧World版の確認記録](docs/v0.1-checks.md)、[旧3人版の確認記録](docs/minimal-checks.md) を参照。

## 構成と参考資料

```text
ww_gg/
  .git/                         既存の履歴・リモートを維持
  README.md                     この案内
  .gitignore                    ローカル専用ファイルの除外を維持
  app.py                        薄いローカルFlask画面
  werewolf/exact.py              公開Board・全Action/Chance・入力条件付け
  werewolf/reports.py            将来報告の厳密キャッシュ
  templates/, static/           HTML・CSS・JS
  tests/                        公開Board・3〜9人／複数狼の計算と昼夜進行の確認
  docs/requirements.md          新版の要件基準
  archive/
    python-legacy/              旧Python版の現内容
    wwExpected-java/            初期Java版の参考スナップショット
    legacy_proto/              以前の試作（既存位置を維持）
    streamlit_proto/            以前の試作（既存位置を維持）
```

- [旧Python版の保存記録](archive/python-legacy/ARCHIVE.md)、[旧README](archive/python-legacy/README.md)、[旧docs](archive/python-legacy/docs/)。
- [Java版の保存記録・コピー一覧](archive/wwExpected-java/README.md)。
- 別フォルダ `gg_ww2` は、従来の実装・QAと要件文書の参照元としてそのまま残す。新版コードとしてコピーしていない。

旧資料は当時の検討・実装の記録であり、新版の完成仕様や正解値の保証にはしない。

## 旧版を復元する方法

旧Python版の未コミット変更を、移動前にローカル保存コミット **`9735ac2b62031ac6cb9f0eacb433fdbced14314d`** に記録した。Java参考資料は別コミット **`d1516c1f38fcb03e8487b5c4edc899c665b6b37f`** で保存した。

旧Python版を元の配置で確認・復元するときは、現在の新版を上書きせず、保存コミットから別ディレクトリのworktreeを作る。

```powershell
git worktree add ..\ww_gg-legacy 9735ac2b62031ac6cb9f0eacb433fdbced14314d
```

実行前に、その復元先ディレクトリが未使用であることを確認する。これは復元時の手順であり、今回worktreeを作成したわけではない。旧版の起動手順は復元した `app/README.md` を参照する。

`.env`、`.venv/`、`.tmp/` は旧リポジトリ直下の現位置に残してあり、今回その内容は読んでいない。Gitの保存対象には含めていないため、別worktreeでの実行環境や秘密設定は別途必要になる。旧コードは作業ディレクトリの `.env` を読むため、archive内をそのまま実行した場合に現在の直下設定を自動で使うとは限らない。

既存のVercel公開連携は別途扱う。旧 `vercel.json` とAPI入口はarchive内に保存し、この整理でデプロイや連携変更は行わない。

## Game / Board 設定画面

TOP で配役とゲームルールを指定し、MAIN 右側の Game で表示・ルール確認、Board で戦略を操作します。設定を閉じるとテーブルが全幅になります。未対応の4ルールは灰色・操作無効、自噛みは既存計算へ接続しています。[UI と検証記録](docs/right-parallel-checks.md)。

## Vercel 試験公開の準備

公開用入口・Python指定・静的配信ビルドと署名キー契約を追加しています。[準備・手動手順・検証](docs/vercel-preparation.md)を参照してください。ユーザーによるキー設定・手動push後、Vercelで試験公開済みです。静的配信の修正と公開QAを進めています。
