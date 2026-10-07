# ww_gg

人狼ゲームの盤面・公開情報と条件から、各行動・各Phaseの厳密な期待勝率を求めるツールを、要件から作り直す。

**公開Boardによるv0.1を反映済みです。** 3〜5人・狼1人で、TOP→昼→夜→翌日の昼→決着の操作を実装しています。計算・Webの22テストと実Edgeブラウザーの確認を完了し、8771のローカルサーバーも更新しました。push・公開は行っていません。

仕様案は [v0.1：素村・狼の3〜5人](docs/v0.1.md)。昼は村勝率max、夜は狼勝率maxが既定、randomは候補等確率による期待値計算です。最大同率へ選択確率を付けず、対象の手動指定は別の操作として扱います。確率・勝率は％を標準にし、分数へ表示切替します。

## 現在の要件

正本は [docs/requirements.md](docs/requirements.md)。素村・狼の3人→4人→5人から確認し、初期対象をTOP、MAINのプレイヤーテーブル・戦略・対象指定・Phase送り・厳密期待値の再計算とする。

Tree可視化は後回し。内部の確率分岐の評価は初期対象に残す。MC推定を厳密期待値の代替にはしない。

## ローカルで確認する

Python 3.12とFlask 3.1.2を使用。現在の環境では既存のFlaskを利用し、依存追加は行っていません。

```powershell
python app.py --port 8771
```

[http://127.0.0.1:8771/](http://127.0.0.1:8771/) を開く。Windowsでは `start.cmd` でも起動できます。ループバックだけで待ち受け、既存 `.env` を読みません。DB・クラウドAPI・外部公開は使用しません。別サービスで使用中のポートは避けてください。

1. TOPで3・4・5人を選び、昼夜の戦略と自噛みRuleを確認して初日昼へ進む。初期値は5人、自噛み不許可。
2. MAINで候補別勝率を確認し、生存対象を1人指定する。情報欄の右で％／分数を切り替えられる。
3. 「夜に進む」「翌日の昼に進む」で、指定Actionの未決着Boardへ進む。全結果が終局なら決着画面へ進む。5人村では昼・夜・翌日昼の3行動を確認できる。
4. 「戦略を反映」は現在以後の計算を変更する。「前のBoardに戻る」は直前の対象と当時の戦略を復元し、そこからの進行を作り直す。

Boardは公開履歴・生存者・人数制約で表し、役職位置を列挙・割当・抽選しません。全候補Treeを終局まで生成してからFractionで評価します。現在Boardの条件付き勝率を主表示し、既終局枝も含めた「開始時点からの累積」を別表示します。この表示は調整可能な仮案です。表示切替は盤面や選択に影響しません。セッションはブラウザーcookieで保持し、サーバー再起動で初期化されます。

```powershell
python -m unittest discover -s tests -v
```

[この版の確認記録](docs/v0.1-board-checks.md)、[旧World版の確認記録](docs/v0.1-checks.md)、[旧3人版の確認記録](docs/minimal-checks.md) を参照。

## 構成と参考資料

```text
ww_gg/
  .git/                         既存の履歴・リモートを維持
  README.md                     この案内
  .gitignore                    ローカル専用ファイルの除外を維持
  app.py                        薄いローカルFlask画面
  werewolf/exact.py              UI非依存の厳密計算
  templates/, static/           HTML・CSS・JS
  tests/                        公開Board・3〜5人の計算と昼夜進行の確認
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
