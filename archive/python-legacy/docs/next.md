# Next

## 現在の方針
- v1 は `manual_tree` モードで進める
- 評価対象は公開情報のみ
- `進む / 戻る / tree click` は node 移動
- `CO / tactics` は draft 編集後に `盤面更新` で tree 編集する

## 直近の優先タスク
1. `manual_tree` 名義への統一を終える
2. `進む / 戻る / tree click` の部分更新化
3. `CO / tactics` を draft + `盤面更新 / キャンセル` フローへ変更
4. current node 表示と Tree 表示の整合を安定化

## メモ
public state と private state を同時に厳密管理し始めると一気に重くなる。
v1 ではそこに踏み込まず、公開情報ベースの手動分岐ツールとして完成させることを優先する。
