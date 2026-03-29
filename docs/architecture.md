# Architecture

## 目的
この文書は、アプリ全体の責務分割を整理するためのもの。
`state-model.md` が「何をどこに保存するか」を扱うのに対し、この文書は「どのファイルが何を担当するか」を扱う。

## 全体方針
現在の `ww_gg` は、次の前提へ寄せる。

- Top は固定設定を編集する画面
- Main は Tree を辿りながら node ごとの公開情報と戦略を編集する画面
- Tree は persistent tree として server 側に保存する
- 既存 node は直接編集せず、編集時は新しい node を生成する
- `進む` `戻る` `Tree click` は `current_node_id` を動かす操作として扱う

## レイヤ構成
現在の `ww_gg` は大きく次のレイヤに分かれている。

1. Entry / Routing
2. State / Tree
3. Domain / Calculation
4. ViewModel
5. Template / CSS / JS
6. Storage
7. Docs

## 1. Entry / Routing
対象ファイル:
- `app/main.py`

責務:
- FastAPI の route 定義
- session の読取/保存
- Top と Main の画面遷移
- Main の編集 API 公開

ここでやること:
- request を受け取る
- session から `game_config` や `ui_state` を復元する
- storage / tree / calculation / viewmodel を呼ぶ
- template へ渡す

ここでやらないこと:
- Tree の永続化ロジック本体
- 勝率計算そのもの
- 役職確率計算そのもの
- 複雑な HTML 条件分岐

## 2. State / Tree
対象ファイル:
- `app/tree_state.py`
- `app/game_tree.py`
- `app/persistent_tree.py`

### `app/tree_state.py`
責務:
- 現在の Tree 走査ロジックを持つ
- `current_node_id` の更新規則を持つ
- Main の navigation 操作を提供する

主要概念:
- `TreeSessionState`
- `TreeNode`
- `current_node_id`
- `root_node_id`

ここでやること:
- 現在 node の取得
- `進む` `戻る` `jump` の移動規則
- 画面用 tree の組み立て

ここでやらないこと:
- server 保存用 record の構築
- HTML 用レイアウト生成

### `app/game_tree.py`
責務:
- `NodeState` / `PlayerState` の定義
- node の公開盤面遷移生成
- state の直列化・復元

主要概念:
- `PlayerState`
- `NodeState`
- `NodeAnalysis`

方針:
- `NodeState` はその node の事実を持つ
- `analysis` は node 生成時に計算して保存してよい

### `app/persistent_tree.py`
責務:
- 画面用 tree から保存用 `StoredTreeRecord` を作る
- `current_node_id` / `nodes_by_id` / `player_configs` を組み立てる

ここでやること:
- `build_stored_tree_record()` のような変換処理
- path ベースの一時表現から node 保存構造への橋渡し

## 3. Domain / Calculation
対象ファイル:
- `app/calculation.py`
- 将来的には `claim_probability.py` などへ分割候補

責務:
- 人数ベースの勝率計算
- 終局判定
- 役職確率計算
- node 生成時の analysis 算出

ここでやること:
- `NodeState` と `GameConfig` から分析結果を返す
- `white_win` `black_win` `player_probabilities` を作る

ここでやらないこと:
- request 処理
- HTML 用表示文言の生成

## 4. ViewModel
対象ファイル:
- `app/view_models.py`

責務:
- 保存済み node と analysis を template が使いやすい形に整形する
- 表示用ラベル・並び順・tone をまとめる

ここでやること:
- `PlayerRow` の組み立て
- option group の組み立て
- Main / Top 用 view model の作成

ここでやらないこと:
- state の永続化
- node の編集
- 勝率計算そのもの

理想:
- `view_models.py` は表示用整形に寄せる
- 計算責務は calculation 層に寄せる

## 5. Template / CSS / JS
対象ファイル:
- `app/templates/*.html`
- `app/static/styles.css`

### Template
責務:
- view model を表示する
- 最小限の分岐だけ持つ

### CSS
責務:
- レイアウトと見た目

### JS
責務:
- popup 開閉
- Main の node 編集 API 呼び出し
- Tree navigation の補助

今後の分割方針:
- `tree navigation`
- `node editing`
- `pure ui toggle`

を分ける。

## 6. Storage
対象ファイル候補:
- `app/storage.py`
- 将来的には `app/repositories/tree_repository.py`
- 将来的には `app/repositories/node_repository.py`

責務:
- Tree の server 側保存
- node / tree / player_config の読取と保存

ここでやること:
- `tree_id` ベースで Tree を保存・復元する
- `current_node_id` を更新する
- node 追加時に親子関係を保存する

現状:
- `StoredTreeRecord`
- `StoredNodeRecord`
- `InMemoryTreeStorage`
- `SupabaseTreeStorage` の空実装

## 7. Docs
対象ファイル:
- `docs/requirements.md`
- `docs/spec_v1.md`
- `docs/state-model.md`
- `docs/architecture.md`
- `docs/structure.md`
- `docs/testing.md`

役割:
- `requirements.md`
  何を作るか
- `spec_v1.md`
  v1 で何をやるか
- `state-model.md`
  状態をどこで持つか
- `architecture.md`
  モジュール責務
- `structure.md`
  ドキュメントの入口
- `testing.md`
  段階ごとのテスト方針

## 現在の課題
今の不具合が起きやすい主因は次の3つ。

1. Main の保存経路が複数ある
- form submit
- fetch + reload
- tree jump

2. node 編集と navigation が近い場所にある
- tactics 変更
- CO 変更
- target 選択
- 進む / 戻る

3. session 中心の設計に、persistent tree 的な要件が混ざっている

## 次のリファクタ方針
### 方針1
`GameConfig` と `TreeState` の責務を明確に分ける。

### 方針2
Tree は server 側へ保存する。

### 方針3
Main の編集系は「現在 node を直接変更する」のではなく、「新 node を生成する API」に寄せる。

候補 endpoint:
- `/main/node/fork-with-tactics`
- `/main/node/fork-with-claims`
- `/main/node/select-target`
- `/main/node/advance`
- `/main/node/back`

### 方針4
`view_models.py` は保存済み node を表示用に整形するだけに寄せる。

## 実装の優先順位
1. `state-model.md` に沿って状態構造を確定する
2. storage 層を追加する
3. `tree_state.py` を `current_node_id` 中心へ寄せる
4. `persistent_tree.py` で保存用 record へ変換する
5. Main の編集 API を再設計する
6. `main.html` の JS を役割ごとに分割する
7. その後に tactics 不具合を再度詰める
