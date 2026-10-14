# 共通の行動評価・選択エンジン：現状棚卸しと後続設計

HEAD7d67696からの読み取り調査。実行コードは変更していない。ユーザー方針：処刑・襲撃・占い・護衛は、設定済み継続方針で未来Boardを評価し、chance期待値を戻し、actor情報集合で集約して選択する同じ構造。同時夜で複数主体がmaxなら相互最大化として扱う。現在タスクの狩人方針は固定uniformのままで範囲を広げない。

## 既に共通化している層

| 層 | 共通部品 | 現在の保証と範囲 |
|---|---|---|
| 行動後の進行順 | action_flow.py:38 resolve_action / :52 action_flow | 取得→夜効果/死亡→終局→投影→朝/昼の継続評価。評価側はpolicyフックを差し込む。選択自体はこのモジュールの外。 |
| chanceのback-up | action_flow.action_flow / morning_flow.py:25 continuation_value | 各物理/朝枝の確率×継続値を加算。良いchance結果をmaxで選ばない。 |
| 継続評価 | information_set_forecast.py:218 act / :316 solve | public law、physical law、observerを分け、同じ再帰で後続方針を評価。root経路も同クラスを継承する。 |
| 単側の候補選択 | policy_choice.py:5 optimal_targets / :12 uniform_policy | 正確なFraction値のmax/min、同率全候補の均等分布。処刑と襲撃が利用。候補生成・情報集合条件付けはcallerが担う。 |
| 狼の情報集合 | actor_information.py:27 WolfInformation / :49 wolf_information_groups | 初期狼roster＋自身の襲撃履歴で集約。未知の狩人/占い結果を平均してからwolf_policyで選択。 |
| 物理/観測/信念の分離 | evaluation_branch.py:6 physical_board、phase_updates.py:23 condition_night_corpse、public_observation_support.py:13 condition_generated_support | 実枝Pと公開ModelA Qを分ける。承認済み観測支持は公開全jointlawでゼロ候補だけ除外、正尤度の大小でQを更新しない。 |
| 夜能力の共通取得/効果 | night_acquisition.py:12 acquire_laws、guard_model.py:181 guarded_outcomes | 公開と本人取得lawを分け、狩人の効果を同じ夜進行へ接続。役職能力は差し込み。 |
| 明け方までの評価 | model_a_public.py:25 horizon_for_action | 最終継続値で選んだ襲撃方針を使い、明け方までの終局質量だけを集計。最終勝率とは別の評価horizon。 |

## まだ共通の自動選択エンジンになっていない層

- information_set_forecast.wolf_policyは公開jointlawのwolf infosetに条件付けて候補村勝率をmin、public_day_max/day_scoresは公開村意思決定でmaxを実装する。候補比較→選択の数学的部品は共通だが、候補/情報集合/目的陣営を受け取る一つのChoiceProblem APIではない。
- Strategy.seer_positionはunvisited→uniformだけ、guard_positionはuniformだけ（exact.py:39～48）。seer_view_forecast.py:14とroot_secret_flow.root_seer_forecastは本人の固定占い先比較、guard_view_forecast.py:13は固定護衛比較。これらは共通act/solveを使うが、公開側の取得・護衛方針を自動maxへ変えない。表に評価値があることをrole max対応完了としない。
- information_set_forecast.generate_morningには既存fake-reportの候補評価・min/同率処理が別にある。chance合成はmorning_flowを共有するが、全行動選択のインターフェースはまだ統一されていない。既存意味を維持し、未定義CO/報告の最適方針を新設しない。
- RootSecretEngineは完全秘密履歴を保持する入口で、既存act/solveを共有する。支持に必要な今夜のkernelと、そのkernelを選ぶ候補継続評価が同じ夜を再参照する未解決箇所がある。現在は未確定maxをPendingにしており、uniformへ代替しない。
- exact.py:731 evaluate_tree / Evaluationは旧参照・比較用の評価入口で、ModelAのactor情報集合を備えた新しい根本法則と同一ではない。互換範囲や比較値を保ったまま、すべて未共通ともすべて完成とも説明しない。

## 上位タスクの差し込み境界

共通ChoiceProblemは合法候補生成、GameRulesによる物理遷移、actorの役職/結果/自身履歴による情報集合、目的陣営、設定済みcontinuation方針を受け取る。候補生成itemは能力ごとに定義するが、期待値back-upや最大化ロジックを役職ごとに複製しない。

1. 各候補のchance枝は確率で積分し、後続Boardの設定済み方針の価値を再帰評価する。role world内で最良候補を選んでから平均するoracle評価はしない。
2. actor infoset内で候補値を集約してから選ぶ。相手固定policyなら単側max/min、既存同率処理を再利用する。現在の狩人uniform対狼maxはこの範囲。
3. 同時夜の占い×狼、狩人×狼、占い＋狩人＋狼がmaxなら、同じdecision stageの各actorの情報集合と混合選択分布を共同で解く設計にする。物理効果の処理順は相手の当夜選択を見て選べることを意味しない。逐次best responseやoracleで代用しない。
4. 村側役職は同じ陣営目的でも秘密を共有できる一人の協調プレイヤーとしない。必要なら分散情報の戦略制約、独立混合/相関の許可、均衡概念、解法、計算量、複数解選択を明示する。単純な二人零和LPへ自動還元できるとは仮定しない。
5. 公開観測支持の生成は解かれた完全public kernelを使い、本人の固定行動介入やprivate factsでpublic kernelを変更しない。現在のmax候補評価と今夜kernelの計算依存を先に整理する。これは固定uniform狩人に対する狼単側maxの計算問題であり、狩人maxを勝手に追加する理由ではない。
6. 一般的な置換同値判定・代表計算を同じエンジンへ組み込み、action/infoset写像とchance多重度を戻す。選択前後の集約順を変えない。

優先順：現在wolf max（task-c857928fd4324a51）→対称性代表計算（task-1123468027e5405e）→共通行動評価・選択エンジン（task-ca6861227f054801）。最後のタスクは相互maxを内包する上位タスクへ更新し、別の相互maxタスクを重複作成しない。現段階は棚卸しと候補整理であり、後続設計の実装は未着手。
## ユーザー確認済みの6段階順序

1. 未確定狩人に対する狼襲撃maxを完了（狩人は固定uniform）。
2. 対称な情報グループの代表計算・重複省略。
3. 期待勝率最大化全体の共通設計：候補/遷移/actor情報/目的陣営と共通評価・選択インターフェース。
4. その全体設計内で同時行動・相互maxを設計：情報集合、混合分布、秘密分離、解法・均衡・計算量。
5. 共通部を小さく実装し、既存処刑/襲撃maxを統合。action_flow、act/solve、continuation_value、optimal_targets/uniform_policy、actor_informationを再利用し、既存部品を作り直さない。
6. 相互maxを小さく実装・検証し、占い/護衛/襲撃へ接続。

3/4で全体の整合を先に決め、5/6で段階検証する。相互maxを先に実装してから全体を共通化する順序にはしない。task-ca6861227f054801を3～6段階の上位タスクとし、重複した別の相互max候補は作らない。現在の1が完了する前に後続実装へ進まない。今回の変更は棚卸しと計画整理のみ。
