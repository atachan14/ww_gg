# 旧資料と docs の経緯

## docs の経緯

- 前身は `G:\source\repos\Python\gg_ww2`。要件は、その `docs/requirements.md` から引き継いだ。旧Python版・Java版・以前の試作はリポジトリの `archive/` にある。
- 2026-03 から開発。v0.1(素村・狼の3〜5人)から始めて、v0.5.2 まで公開。docs は作業ごとの記録として積み重なり、2026-10-29 には docs 直下に233本あった。
- 2026-10-29 に Dot が入口(README、CURRENT、HANDOFF、CATALOG)を整備した。同じ日、Claude Opus 5.5 がそれまでの docs 一式を `docs/archive/20261029/` に移し、今の docs を作り直した。

## 旧資料の読み方

`docs/archive/20261029/` の主なもの:

| ファイル | 中身 |
|---|---|
| `README.md`、`CURRENT.md`、`HANDOFF.md`、`CATALOG.md` | Dot が 2026-10-29 にまとめた入口と、全233本の分類 |
| `requirements.md` | ユーザーが確定した要件の台帳(v0.1〜v0.3 のころが中心。今の実装の一覧ではない) |
| `backlog.md` | 後続の設計・UI の予定と、名称などの確定事項 |
| `v0.1.md`〜`v0.5.2.md` | 各版の仕様と検証の記録 |
| `co-group-model.md`、`candidate-policy-coherence.md`、`simultaneous-action-design.md` | 計算モデルの設計 |
| `current-model-structure-review.md`、`shared-symmetry-transition-plan.md` | モデルの構造のレビューと、移行の台帳 |
| 性能の記録 | [../PERFORMANCE.md](PERFORMANCE.md) の末尾 |

## 読むときの注意

- 「最新」「確定」と書いてあっても、その記録の時点のこと。後のユーザーの決定が優先する。
- 提案・調査の文書は、採用されたルールではない。それだけを理由に実装しない。
- テストの件数や時間は、その時点・その環境の記録。
- ルール訂正の経緯: 占い師の対象は「夜の開始時点で生きている人」(2026-10-20 のユーザーの訂正)。それ以前の「死んだ人も対象にできる」記録(`corpse-scan-rule-fix.md`)は、対象の合法性については古い。
- docs の中の Slack のメッセージ ID は、採用時の会話の索引。
