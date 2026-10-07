# ww_gg

人狼ゲームの公開情報から、各行動に対する期待勝率を計算するツール。

## 現在のドキュメント
- `docs/requirements.md`: プロジェクト概要、画面構成、用語、計算方針
- `docs/spec_v1.md`: v1 の実装範囲と完成目標
- `docs/state-model.md`: 状態構造の整理
- `docs/architecture.md`: モジュール責務の整理
- `docs/deploy-vercel-supabase.md`: Vercel Hobby + Supabase の導入メモ
- `docs/testing.md`: 段階ごとのテスト方針
- `app/runtime_config.py`: 環境変数の読込
- `app/storage.py`: server 保存型へ寄せるための storage 土台
- `app/README.md`: 新実装の作業場所
- `archive/legacy_proto/README.md`: 旧試作コードの扱い


## ディレクトリ構成
```text
/
  README.md
  requirements.txt
  .env.example
  index.py
  vercel.json
  docs/
    requirements.md
    spec_v1.md
    state-model.md
    architecture.md
    deploy-vercel-supabase.md
    testing.md
  app/
  supabase/
    schema.sql
  archive/
```

## メモ
- 確定要件の参照先は `docs/requirements.md` と `docs/spec_v1.md`
- 状態と責務の整理は `docs/state-model.md` と `docs/architecture.md`
- Vercel / Supabase の準備は `docs/deploy-vercel-supabase.md`
- テスト方針は `docs/testing.md`
- 旧試作コードは `archive/legacy_proto/` に退避済み
