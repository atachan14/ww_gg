# 旧Python版の保存記録

再設計のため、`ww_gg` 直下にあった旧Python版の現内容を、この `archive/python-legacy/` に退避した。旧ファイルの内容は変更していない。元の `README.md` もそのまま保存している。

- 元の場所: `G:\source\repos\Python\ww_gg`
- 移動前の基準HEAD: `87dcad1c176fc154f2edfcf311fe792dd670dfd4`
- 未コミット変更を含む旧版保存コミット: `9735ac2b62031ac6cb9f0eacb433fdbced14314d`
- 保全対象の内容とSHA-256: [ARCHIVE-SHA256.json](ARCHIVE-SHA256.json)。ソース・docs・設定50件を移動前後で照合した。
- 移動対象: `api`, `app`, `docs`, `supabase`, `tests`, `.vscode`, `.env.example`, `.gitignore`, `index.py`, `README.md`, `requirements.txt`, `vercel.json`。
- 生成キャッシュ25件はディレクトリと共に移動して保全したが、内容の読取・Git追加はしていない。
- `.env`、`.venv/`、`.tmp/` は元の直下に残した。秘密情報・環境の内容は読んでいない。
- 既存 `.git` とリモート、`archive/legacy_proto/`、`archive/streamlit_proto/`、`archive/wwExpected-java/` は移動していない。
- 旧Vercel設定とAPI入口は原文のまま保全した。公開設定の解除・変更・デプロイはしていない。

復元方法は [直下のREADME](../../README.md) を参照する。別worktreeで保存コミットを開くと、旧Python版のソース・docs・テストを移動前の配置で確認できる。

旧版の実行・テスト・依存インストールは今回行っていない。保存コミットも、この旧実装の正しさを保証するものではない。
