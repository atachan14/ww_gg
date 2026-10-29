# 共通化の最終監査

監査開始HEAD: `8025530d338b8b6fdfb3aeb7db4aa9bb677e073f`。対象は復旧コピーのみ。現行仕様を変更せず、入口、公開/本人Table、日/夜遷移、報告/履歴条件付け、選択集約、cachekeyを確認した。

## 1. 現行仕様のまま安全に削れる重複 — 整理済み

- 本人Tableの占い・狩人・狼に繰り返されていた初日/保存履歴の入口準備を `root_secret_flow.py:203 prepare_root_entry` に集約。公開の保存履歴入口も同じ関数を使う（`private_adapter.py:47`、`model_a_public.py:97`）。未対応は `None` で従来入口を保持し、対応範囲内の生成失敗は `FuturePending` のまま返す。失敗時に旧計算へ置き換えない。
- 初日と途中Boardで重複していた同じjoint-lawの全体値・対象行・夜明け値の計算を `root_secret_flow.py:310 root_branch_forecast` に集約。初日の `root_screen_forecast`（同:178）は適用範囲と従来の外側時間予算を保持する薄い入口にした。

## 2. 新経路の未対応範囲を支える旧経路 — 維持

- `model_a_public.py:54 public_forecast` と `information_set_forecast.py:44`：既存max、固定CO、役職・履歴圧縮と対称性による計算短縮を担う。新経路の `RootSecretEngine`（`root_secret_flow.py:112`）は潜伏取得/護衛/襲撃の共同履歴を保持する。見た目のsolve/act呼出しは似ていても、前提と圧縮の許可範囲が違い、一つに寄せると秘密履歴の消失または旧maxの仕様変更になる。
- `seer_view_forecast.py:14` と `root_secret_flow.py:335`：旧CO/allの取得台帳と、完全joint lawの公開Q/物理P・死亡前の介入支持は契約が異なる。旧版は対象ごとの作業予算や既存Pending/ValueErrorも持つ。API/失敗契約まで変更する大きな統合は今回行わない。狩人の実計算は既に `guard_view_forecast.py:13` を両経路で共有している。
- `guard_history_prior.py:31 seed_history`：既存maxで証明済みの限定的な潜伏履歴生成を支える。新しい保存履歴再生（`root_secret_flow.py:247`）の均等生成に置き換えない。
- `seer_future_forecast.py:30`、`seer_future_bridge.py:8`、`wolf_view_forecast.py:18` と `exact.py:587`：既存の固定方針/能力なしの参照API・比較テスト・互換exportを担う。Model Aの狼情報集合を扱う新評価と同じ意味ではなく、削除対象にしない。

## 3. 設計決定や新機能が必要な残件 — 今回は実装しない

- 新経路max・同時複数max（`root_secret_flow.py:82`）、複数狩人・連続護衛なし（`guard_model.py:26`）、未定義CO/初期偽報告/複数偽報告の生成方針（`morning_publications.py:79`）。均等への置換や未定義方針の補完はしない。
- 長いGJ履歴の計算量：共同履歴を削除せず保持するため増大する。より小さい十分統計へ圧縮できるかは各方針・本人情報の同値性の証明が必要。上限を増やしたり旧圧縮を流用するだけの変更はしない。

## 既に共通であり、分離を維持する境界

- 日/夜の物理順序は `action_flow.py:38 resolve_action` / 同:52 `action_flow`、公開/本人の能力取得は `night_acquisition.py:12 acquire_laws`、護衛効果は `guard_model.py:129 guarded_outcomes` を共有している。`model_a_public.py:25 horizon_for_action` は全体・本人の夜明け評価で共用。
- 公開観測は `seer_manual.py:89 replay` / `seer_acquisition.py:132 condition_publications` を共用。将来報告生成は `morning_publications.py:79 future_publications`、本人の物理枝への尤度移送は `information_weights.py:10 observer_report_weights`。観測、生成、介入を一つにすると公開Qと物理Pを混ぜるため、その分離は必要。
- 狼の秘密を使わない集約境界は `actor_information.py:49 wolf_information_groups`、選択は `policy_choice.py:5 optimal_targets` / 同:12 `uniform_policy`。`exact.py:564 aggregate_values` は行動ID/同点分布を返さないscalar値APIであり、方針選択とは役割が異なる。
- 公開入力のserializerは `public_prior.py:10 public_history_key` に集約済み。公開結果cacheと取得台帳cache（同:38）は出力型・依存引数が違う。内部scalar圧縮key（`medium_value_key.py:82`、`joint_value_key.py:63`）も適用条件つきであり、公開cacheに本人観測を入れたり共同履歴を無条件に圧縮しない。

## 判定

**現行対応範囲で必要な整理は済んだ。** 残る並列入口は仕様・情報所有・互換性・予算契約の境界であり、小さな重複を理由に一括抽象化しない。今回の変更は入口準備と同じjoint-law予測の共用に限定。対応範囲の拡張、maxの均等化、push/deployは行わない。

検証: 関連29テスト成功（18.422秒）、対象上の全529テスト成功（180.003秒）。専用18801の所有元を再確認し監査後コードで再起動（PID18076）。HELP current/design と実HTTP MAINは200、5人均等MAINは7/15（46.67%）を維持。max等の新実装・push/deployなし。
