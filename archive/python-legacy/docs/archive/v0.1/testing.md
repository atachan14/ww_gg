# Testing

## 今の段階で入れるテスト
- unit test
  - `app/calculation.py`
  - `app/game_tree.py`
  - `app/tree_state.py` の純ロジック
  - `app/persistent_tree.py` と `app/storage.py` の保存用変換
- manual test
  - Main の操作導線
  - JS の popup / toggle / select 保存
- deploy smoke test
  - Vercel で起動するか
  - Supabase へ接続できるか

## 段階ごとのおすすめ
### 1. 純ロジックを触る段階
対象:
- 勝率計算
- 終局判定
- node 遷移
- serialize / deserialize

やること:
- `python -m unittest discover -s tests`
- 変更した関数に対応する unit test を追加する

### 2. Main の保存経路を触る段階
対象:
- tactics 保存
- CO 保存
- Tree click
- 進む / 戻る

やること:
- unit test に加えて manual test を行う
- 最低限見る項目
  - Top -> Main で初期化されるか
  - tactic が node ごとに残るか
  - CO が node ごとに残るか
  - 進む / 戻る / Tree click で current node がずれないか

### 3. persistent tree / storage を触る段階
対象:
- node の fork
- current_node_id 更新
- storage save / load

やること:
- storage 単体 test を追加する
- `build_stored_tree_record()` の node 保存結果を確認する
- `InMemoryTreeStorage` と `SupabaseTreeStorage` で共通の振る舞いを確認する
- fork 後に親 node が変わっていないことを確認する

### 4. Vercel / Supabase 接続段階
対象:
- env 読込
- DB schema
- app 起動

やること:
- ローカルで `.env` を使って起動
- Vercel の preview deploy で表示確認
- Supabase に 1 件だけテスト tree を保存 / 読込する

## 今の最小コマンド
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## 方針
- UI の見た目だけの変更では重い自動テストを増やしすぎない
- 壊れやすい核心ロジックから固定する
- persistent tree 化したら storage 周りの test を最優先に増やす
