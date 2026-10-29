# ③/⑤：既存の偽霊能max選択の共通化・第1単位

基準：公開済みv0.5 `277f37a0d61f39a67800ab08a99888136c5383e2`。
作業branch：`work/max-choice-common`。今回の変更はローカルのみ、公開対象ではない。

## ③の設計と実装の差分

既存の役割分離を再実装しない。

| 設計の境界 | v0.5時点の実装 | 今回の扱い |
|---|---|---|
| 本人情報集合と公開Q/物理P | actor_information、ActionInputs/ContinuationInputs、公開/本人入口 | 維持 |
| 行動・取得・物理枝・報告の順序 | action_flow、night_acquisition、guard_model、morning_flow | 維持 |
| 完成した全候補から同率最善手を選ぶ | policy_choice.optimal_targets / uniform_policy。処刑・襲撃・root方針証明が使用 | 偽霊能報告の残る2箇所も接続 |
| 方針依存・完全方針の証明 | policy_dependencies、policy_certificates、WolfProfileResolver/CandidateRules | 既存の限定範囲を維持。一般相互maxへ拡張しない |
| 完全入力cacheと未完結果 | 完成値のみ保存、完全入力/方針/観測者/証明modeを区別 | 維持 |
| DecisionValue/DisplayValue、ExactActionValue/Dependenciesの全APIでの型分離 | 公開採点/本人表示は呼出し境界で分離済みだが、全旧API共通の新しい結果型には統一されていない | 残差。今回の小単位へ混ぜない |
| 一般の同時複数maxと未選択の均衡/共同則 | 一般実装なし | 保留 |

古い設計文書の「まだ未接続」などは当時の段階記録である。
既存入口・完全方針証明・root適用を改めて作り直すものではない。

## 実施した小単位

`InformationSetForecast.generate_morning` と旧 `wolf_view_forecast` の
公開偽霊能報告選択に残っていた手書きmin/同率抽出/1件あたりの均等化を、
既存の `optimal_targets(maximize=False)` と `uniform_policy` へ接続した。
狼側の村勝率最小化という既存契約をそのまま使用する。

各完全報告指示の期待値を最後まで採点してから選択する順序は変えない。
同じ勝率の別指示を値だけで統合しない。選択指示の質量を既存の各chance枝へ
掛け、既存 `merge_report_outcomes` で同じ公開報告ベクトルを合算する。
本人への尤度移送はその後であり、本人秘密による公開ランキング変更はない。
randomの報告則、真結果、合法手、能力、公開重み、履歴、予算、Pendingは不変。

既存scalar APIである `exact.aggregate_values`、`reports.py` のmin/平均は、
行動IDや同点分布を返すAPIではない。見た目の重複だけで方針選択へ統合しない。
旧本人評価器の他の公開ランキング/合法候補選択にも手書き選択は残るが、
候補の合法性・本人介入・旧圧縮との契約を確認する別単位とする。

## 回帰と根拠

- 全同率の異なる報告指示で、元のrandom全指示混合と公開枝が完全一致。
  同じ黒報告が質量3/4、内部の生存狼1/2人が2/3・1/3となる例を維持。
- 唯一最善の報告は指示全体の期待値で選ぶ。途中の候補評価がPendingなら
  完成した選択やmorning cacheを返さない。
- 霊能2COの狼本人2視点で、襲撃候補は真霊への1、他候補は報告maxで1/2、
  randomで3/4。公開v0.5コードをメモリ上の独立参照として全候補一致を確認。
- 関連16テストは2.690秒で成功。全631テストも315.739秒で成功。
  全体ログ：`.artifacts/integration-validation/max-common-step1-full.log`。

戦略タグ、真偽基準、COグループ、新しい入力受理、占い/護衛maxの仕様は変更しない。
push/deployなし。v0.5の公開版はそのまま維持する。
