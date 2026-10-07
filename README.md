# ww_gg

人狼ゲームの盤面・公開情報と条件から、各行動・各Phaseの厳密な期待勝率を求めるツールを、要件から作り直す。

現在は旧版の保存と要件整理まで。**新版のアプリコードはまだ実装していません。** 技術選定・依存インストール・テスト・サーバー起動・公開は、この整理には含みません。

## 現在の要件

正本は [docs/requirements.md](docs/requirements.md)。素村・狼の3人→4人→5人から確認し、初期対象をTOP、MAINのプレイヤーテーブル・戦略・対象指定・Phase送り・厳密期待値の再計算とする。

Tree可視化は後回し。内部の確率分岐の評価は初期対象に残す。MC推定を厳密期待値の代替にはしない。

## 構成と参考資料

```text
ww_gg/
  .git/                         既存の履歴・リモートを維持
  README.md                     この案内
  .gitignore                    ローカル専用ファイルの除外を維持
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
