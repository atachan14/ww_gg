# Spec v1

## 目的
公開情報だけを使って、人狼盤面の期待値を追える `manual_tree` モードを作る。

v1 では、各 player の private state は扱わない。
狼・占い・霊能などの行動判断も、個人視点ではなく公開盤面ベースの評価に寄せる。

## モード名
旧 `parallel` は使わず、以後は `manual_tree` と呼ぶ。

意味:
- user の操作によって node を追加する
- tree を丸ごと切り替えるのではなく、現在 node から枝を増やす
- `進む / 戻る / tree click` は node 移動
- `盤面更新` は tree 編集

## v1 の前提
- 評価対象は公開情報のみ
- private state は保持しない
- 同じ公開情報なら同じ盤面として扱う方向を目指す
- 到達率は `ChanceNode` のみ表示する
- `ChoiceNode` は確率表示なし

## node の扱い
### node 移動
- `進む`
- `戻る`
- `tree click`

これらは既存 node 間の移動として扱う。

### tree 編集
- CO の変更
- tactics の変更
- 将来的な盤面入力変更

これらは即時反映ではなく、編集中の draft として持つ。
`盤面更新` を押したときに、直前の node を確認し、必要があれば既存盤面用の manual_node を作成した上で、その並列に manual_node として追加する。
`キャンセル` で draft を破棄する。

## UI / UX 方針
- Main は current node を表示する
- TreeView では current node をアウトラインで強調する
- `進む / 戻る / tree click` は将来的に部分更新化する
- `CO / tactics` は `盤面更新 / キャンセル` を伴う編集フローにする

## v1 の優先タスク
1. `manual_tree` への名称統一
2. `進む / 戻る / tree click` の部分更新化
3. `CO / tactics` を draft 編集 + `盤面更新` フローに変更
4. current node 表示と Tree 表示の整合を安定化
5. 公開情報ベースの期待値計算を v1 範囲で固める

## v1 でいったん扱わないもの
- 各 player の private state 管理
- full-tree mode の全分岐生成
- CO タイミングや能力結果開示の全枝展開
- 個人視点での最適行動

## メモ
今回の難所は、公開情報だけで進めたい設計と、役職ごとの private state 依存の行動が噛み合わないことだった。
v1 ではそこを無理に解かず、公開情報ベースの手動分岐ツールとして成立させることを優先する。
