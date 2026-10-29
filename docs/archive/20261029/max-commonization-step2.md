# ⑤：旧本人評価器の対象選択共通化・第2単位

基準：第1単位 `e41b999792467019301c26ca0d9b78b8bba84032`。
作業branch：`work/max-choice-common`。checkoutの `.agents`、`.codex`、
`skills` と祖先AGENTS.mdは存在せず、追加のローカル手順はなかった。
既存の共通設計と第1単位の記録を確認して進めた。

## 統合したもの

旧 `wolf_view_forecast` の `private_solve` と `solve` に残っていた、
公開候補値から最善対象を抽出する手書きmax/minと同率抽出を、既存の
`policy_choice.optimal_targets(scores, maximize=phase=='day')` に接続した。
昼は村勝率最大・夜は最小という契約と、全同率候補の順序・個数を維持する。

合法手生成や公開採点を統合していない。`solve` は従来通り本人にとっての
合法候補を先に絞り、その中の公開評価値で選択する。`private_solve` は
observerの秘密を公開採点へ渡さず、公開指示が本人に不合法なら従来どおり
`seer_view_public_instruction_private_illegal` のPendingを返す。
都合のよい別候補を選び直す規則は追加しない。
randomは全合法候補を保持。本人利得の均等平均、物理枝、報告生成、cache、
予算、例外理由は変更しない。第1単位の報告選択共通化も維持する。

## 専用回帰

- 非対称な7人開始盤面の後続夜で、公開最小値のP3（本人狼、1/3）を
  先に除外し、合法なP4/P5/P6（各3/5）を全て選ぶ。min後の除外ではない。
- 別の同じ公開夜で、maxならP1のみ、randomならP1/P5/P6全てを維持する。
- observerの取得介入P2/P3で本人値67/80・121/140を維持し、同じ初期公開盤面の
  採点は一致する。後続の公開占い対象/結果が違う盤面を、死亡履歴だけで
  同一視して比較しない。
- 混合狼人数を持つobserverで、本人に不合法な公開指示は従来のPendingを維持。
- e41b999の実コードをメモリ上の独立参照として、昼夜max/randomの4設定と
  observer2入力の全結果・全traceが一致することを確認した。

## 残件と仕様判断

- 旧本人評価器のこの2箇所の対象選択は共通化済み。公開ランキングの
  scalar集約（`public_values` のmin/max/平均）は、対象ID/同率方針を返さない
  値APIなので別契約のまま維持する。合法性と採点を分ける境界も維持する。
  これらは未決仕様による停止ではなく、役割の異なる部品である。
- ③のDecisionValue/DisplayValue、ExactActionValue/Dependenciesを全旧APIへ
  型として揃える作業は残る。既存の意味を保持した段階的整理は技術設計・回帰の
  対象であり、新しいゲーム規則の選択は今回必要なかった。
- 一般相互maxの共同法則・同率/混合・複数解選択、新しい占い/護衛max、
  真偽基準・戦略タグ・入力受理・COグループの再設計は別途保留。
  これらは仕様判断が必要で、今回の共通化へ混ぜない。

専用・関連29テストは4.983秒、最終全635テストは318.036秒で成功。
全体ログ：`.artifacts/integration-validation/max-common-step2-full.log`。
ローカルcommitのみ、push/deployなし。
