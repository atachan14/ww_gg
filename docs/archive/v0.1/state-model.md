# State Model

## 目的
この文書は、`ww_gg` がどの状態をどこで持つかを整理するためのもの。
今後は「override を当てて同じ node を書き換える」よりも、
「編集したら新しい node / 新しい世界線を作る」前提で設計する。

## 採用したい考え方
- Tree は 1 回生成したら、その中の既存 node は編集しない。
- Main では `current_node` を見ているだけにする。
- CO や tactics を変更したいときは、現在 node から新しい node を作る。
- 元の node も残し、新しい node は別世界線としてぶら下げる。
- `進む` `戻る` `Tree click` は、基本的に `current_node_id` を動かすだけにする。

この前提では、
- 既存 node の計算結果
- 編集後の新規 node の計算結果
が混ざりにくい。

## State構造図 v0.2.2
- 保存状態
  - Session
    - game_config
      - role_counts
      - rules
    - ui_state
      - top
        - option_open_states
      - main
        - white_details_toggle
        - black_details_toggle

  - Server Storage
    - tree_state
      - tree_id
      - current_node_id
      - player_configs
        - player_config
          - index
          - name
        - player_config...
      - nodes
        - node
          - node_id
          - parent_node_id
          - child_node_ids
            - node_id
            - node_id...
          - state
            - day_phase
            - players
              - player
                - index
                - public_state
                  - alive
                  - claim_role_keys
                  - status
              - player...
            - tactics
          - analysis
            - min_wolf
            - max_wolf
            - white_win
            - black_win
            - reach_probability
          - player_probabilities
            - player
              - white_probabilities
              - black_probabilities
            - player...
          - branch_meta
            - selected_target
            - branch_label
        - node...

- UIローカル状態
  - main
    - claim_popup_open_player
    - 一時的な hover / focus
  - top
    - 一時的な入力中状態

## この構造の意図
### `game_config`
Top で決める固定設定だけを持つ。

含めるもの:
- `role_counts`
- `rules`

含めないもの:
- `tactics`
- CO
- current node

理由:
- `tactics` は node ごとに変えたい。
- CO も node ごとに変化する。

### `tree_state`
Main で進行する Tree の正本を持つ。

含めるもの:
- `tree_id`
- `current_node_id`
- `player_configs`
- `nodes`

役割:
- Main と Tree の表示対象を決める。
- node 間の親子関係を保持する。
- 現在見ている世界線を特定する。

### `player_configs`
全 node 共通で持ちたいプレイヤー設定。

候補:
- `index`
- `name`

理由:
- Day2 で名前を変更しても、Day1 を含む全 node に反映したいから。

### `node.state`
その node における公開盤面そのもの。

含めるもの:
- `day_phase`
- `players`
- `tactics`

ここは「事実」を持つ層。

### `node.analysis`
その node に対して計算した全体分析値。

候補:
- `min_wolf`
- `max_wolf`
- `white_win`
- `black_win`
- `reach_probability`

この構造では、analysis は保存対象にしてよい。
理由:
- 既存 node を後から直接編集しない前提だから。
- node 生成時に計算して確定させれば、他 node と衝突しにくいから。

### `node.player_probabilities`
各 player の役職確率を持つ層。

含めるもの:
- `white_probabilities`
- `black_probabilities`

理由:
- `alive` や `claim_role_keys` とは別の「計算結果」だから。
- `player` 本体の事実と混ぜずに保持したほうが見通しがよい。

## 保存するもの / 保存しないもの
### 保存するもの
- `game_config`
- `tree_state`
- `node.state`
- `node.analysis`
- `node.player_probabilities`
- `player_configs`

### 保存しないもの
- popup の開閉
- hover / focus
- レイアウト計算済みの `tree_view`
- 一時的なフォーム操作状態

## Main での操作と state 更新
### `進む`
- `current_node_id` を次 node に移動する
- 既存 node は変更しない

### `戻る`
- `current_node_id` を親 node に戻す
- 既存 node は変更しない

### `Tree node click`
- `current_node_id` をクリック先 node に切り替える

### CO / tactics 変更
- 現在 node を直接書き換えない
- 現在 node を親にした新 node を生成する
- 新 node の `state` と `analysis` を保存する
- `current_node_id` を新 node に移す

## サーバー保存型について
この v0.2.2 では、Tree は server 保存型へ寄せる前提がかなり自然。

メリット:
- session に大きい Tree を詰め込まなくてよい
- node 単位で保存・参照しやすい
- 世界線分岐をそのままデータ構造で表現しやすい
- `current_node_id` を軸に Main / Tree / API を統一しやすい

デメリット:
- 保存先の実装が必要
- 初期コストは少し増える

ただし、今後また構造リファクタするコストを考えると、
Tree についてはこのタイミングで server 保存型に寄せる判断は有力。

## 現時点の暫定結論
- `GameConfig` は session 保存でよい
- `Tree` は server 保存型へ寄せる方向でよい
- Tree は `current_node_id` 中心で扱う
- CO / tactics 変更は新 node 生成として扱う
- `analysis` と `player_probabilities` は node に保存してよい

## v0.2.1以前の文章について
この文書の中では、v0.2.1 以前の説明はもう残さなくてよい。
理由:
- override 型の発想が中心で、現在の前提とズレている
- 併記すると読み手が混乱しやすい
- 比較履歴が必要なら Git の履歴で追える

そのため、このファイルは「現時点の正本」だけを残す方針にする。
