# ww_gg

人狼ゲームの盤面・公開情報と条件から、各行動・各Phaseの厳密な期待勝率を求めるツールを、要件から作り直す。

**素村2・狼1のローカル最小版を実装しました。** TOP→初日昼のMAIN→指定処刑→決着画面を確認できます。4人以降、CO・能力、公開情報の編集、Tree可視化、永続保存は今回の対象外です。

## 現在の要件

正本は [docs/requirements.md](docs/requirements.md)。素村・狼の3人→4人→5人から確認し、初期対象をTOP、MAINのプレイヤーテーブル・戦略・対象指定・Phase送り・厳密期待値の再計算とする。

Tree可視化は後回し。内部の確率分岐の評価は初期対象に残す。MC推定を厳密期待値の代替にはしない。

## ローカルで確認する

Python 3.12とFlask 3.1.2を使用。現在の環境では既存のFlaskを利用し、依存追加は行っていません。

```powershell
python app.py --port 8771
```

[http://127.0.0.1:8771/](http://127.0.0.1:8771/) を開く。Windowsでは `start.cmd` でも起動できます。ループバックだけで待ち受け、既存 `.env` を読みません。DB・クラウドAPI・外部公開は使用しません。別サービスで使用中のポートは避けてください。

1. TOPで村人2・狼1、等確率戦略を確認し、初日昼へ進む。
2. MAINの広いプレイヤーテーブルで各人の狼確率 `1/3`、処刑した場合の村期待勝率 `1/3` を確認し、対象を1人指定する。
3. 「夜に進む」を押す。この3人例は処刑直後に全枝終局するため、決着画面の情報欄に村 `1/3`・狼 `2/3` が表示され、夜には進まない。
4. 「処刑前に戻って再確認」で元の条件と選択を再表示し、別対象を確認できる。現実のゲーム履歴の訂正ではなく、最小例の再確認操作として扱う。

役職配置3通りの確率をFractionで保持し、実役職や結果を1つ抽選しません。役職確率・対象別期待勝率・戦略全体の勝率は区別しています。セッションはローカルのブラウザーcookieで保持し、サーバー再起動で初期化されます。

```powershell
python -m unittest discover -s tests -v
```

[最小版の確認記録](docs/minimal-checks.md) を参照。

## 構成と参考資料

```text
ww_gg/
  .git/                         既存の履歴・リモートを維持
  README.md                     この案内
  .gitignore                    ローカル専用ファイルの除外を維持
  app.py                        薄いローカルFlask画面
  werewolf/exact.py              UI非依存の厳密計算
  templates/, static/           HTML・CSS・JS
  tests/                        3人最小版の確認
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
