# Structure

このファイルは、構造ドキュメント群の入口メモとして使う。

## 参照先
- `requirements.md`
  プロダクトとして何を作るか
- `spec_v1.md`
  v1でどこまで実装するか
- `state-mode.md`
  状態をどこで持つか
- `architecture.md`
  モジュール責務をどう分けるか

## 今の方針
- Topは固定設定を編集する画面
- MainはTreeを辿りながらnodeごとの公開情報と戦略を編集する画面
- 計算結果は保存せず、状態から毎回導出する

## 補足
`structure.md` は概要の入口として残し、詳細は `state-mode.md` と `architecture.md` に寄せる。
