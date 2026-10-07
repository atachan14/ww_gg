# Vercel + Supabase Setup

この文書は、`ww_gg` を `Vercel Hobby + Supabase` で動かすための最小セットアップ手順をまとめたもの。

## 方針
- アプリ本体は Vercel Hobby にデプロイする
- Tree の保存先は Supabase Postgres を使う
- Top の軽い設定や一部 UI 状態は session / browser 側に残してもよい
- Tree / Node / PlayerConfig は server 側保存へ寄せる

## 1. Supabase project を作る
1. Supabase で新規 project を作る
2. `SQL Editor` で `supabase/schema.sql` を実行する
3. 次の値を控える
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_DB_URL`

## 2. Vercel project を作る
1. GitHub のこの repository を Vercel に import する
2. Framework Preset は Python / Other のままでよい
3. Root は repository root のままにする
4. Environment Variables に `.env.example` の値を登録する

## 3. Vercel の Python entrypoint
- root の `index.py` を Vercel の入口にする
- `index.py` は `app.main:app` を再 export するだけにしている

## 4. ローカル確認
1. `.env` を `.env.example` から作る
2. まずは今まで通りローカル起動する
3. 次の段階で DB 接続コードを足したら、Supabase への read/write を確認する

## 5. 次にやること
- `app/storage.py` の `SupabaseTreeStorage` を実装する
- `TreeState` を `current_node_id` 中心へ寄せる
- `tree_nodes` への保存 / 読込 repository を作る
- Main の node 編集 API を `fork` 前提に切り直す

## メモ
- Vercel Hobby は無料で始めやすいが、serverless 的な制約は意識する
- Supabase は最初は JSON-heavy な schema で始め、あとで正規化してもよい
- `analysis` と `player_probabilities` は persistent tree 前提なら保存してよい

## 6. どこまで Codex ができるか
- repository 内のコード変更、schema 作成、設定ファイル追加は Codex 側で進められる
- Supabase project 作成、SQL Editor 実行、Vercel project 作成、環境変数登録はアカウント操作が必要なのでユーザー側の操作が必要
- ただし、入力すべき値や手順は Codex 側でその都度整理できる

