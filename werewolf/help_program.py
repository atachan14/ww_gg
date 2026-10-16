"""Technical HELP metadata; no solver or session operations."""
PAGES={'index':'プログラム詳細（仮）','current':'プログラム詳細（現在実装）',
       'model':'確率モデルと情報集合','flow':'処理フローと評価アルゴリズム',
       'reference':'型・関数リファレンス','verification':'再現例と検証',
       'design':'プログラム詳細（設計案）','terms':'共通用語・記法'}
AUDIT_VERSION='v0.5.1（実装基準 fe4bd0b）'
REVIEW_VERSION='97d0ed4'
PUBLIC_SHA='fe4bd0be30f2c5c5c78fd61c6545031542a9e0b4'
TERMS=(('world','役職世界 W','狼・霊能・占い師・狩人の位置を表すマスクの組。一つを実役職として抽選してはいない。'),
       ('public','公開信念 Q','公開Boardの役職候補と重み。狼の行動選択尤度で役職を推測しないmodel Aの入力。'),
       ('physical','物理分布 P','候補世界を真と置いて、政策と能力の確率から列挙する結果・情報状態の分布。'),
       ('information','情報集合 I','行動者に区別できない状態の集合。同じ情報集合には同じ政策を使う。'),
       ('policy','政策 π(a | I)','情報集合に基づく行動の分布。maxの同率の期待勝率最大化候補は均等化する。'),
       ('private','本人記録 K','本人の取得結果・護衛先・襲撃先。公開信念を変更する入力ではない。'),
       ('pending','Pending','未対応・情報不足・予算超過による未計算。確率0や不可能な枝とは異なる。'))
REFERENCES=(('公開状態','exact.py','Board / initial_board / replace_worlds','test_exact'),
 ('世界と記録','seer_acquisition.py','Hypothesis / normalize / from_board','test_guard_hidden'),
 ('夜名簿','seer_future_uniform.py','TrueScanState','test_guard_history_flow'),
 ('本人条件','private_view.py','PrivateView / condition_private','test_private_view'),
 ('公開評価','model_a_public.py','public_forecast / horizon_for_action','test_model_a_public'),
 ('情報集合・再帰','information_set_forecast.py','wolf_policy / solve / scalar','test_information_set_model_a'),
 ('共通行動順序','action_flow.py','NightFrame / resolve_action / action_flow','test_action_flow'),
 ('物理継続の受渡し','evaluation_branch.py','ActionInputs / ContinuationInputs / physical_board','test_evaluation_branch'),
 ('本人条件・狼情報集合','actor_information.py','condition_actor_state / WolfInformation / wolf_information_groups','test_actor_information'),
 ('根の完全秘密状態','root_secret_flow.py','prepare_root_secrets / root_actor_view / observe_root_public / step_root_action / root_secret_value','test_root_secret_flow'),
 ('設定方針下の期待値同率選択','policy_choice.py','optimal_targets / uniform_policy','test_root_secret_flow'),
 ('初日均等画面の接続','root_secret_flow.py','root_screen_eligible / root_screen_forecast','test_root_secret_screen'),
 ('護衛と公開更新','guard_model.py','GuardContext / guarded_outcomes / condition_guard_observation','test_guard_hidden'),
 ('混合の補助API','guard_history_mixture.py','GuardHistoryMixture / enumerate_guard_history_mixture','test_guard_history_mixture'),
 ('固定均等の共同分布評価（大規模履歴は予算制限あり）','fixed_actor_continuation.py','fixed_uniform_action_value','test_uniform_fixed_backup'),
 ('計算予算','calculation_budget.py','calculation_budget / tick','test_mixed_flow_memo'))
FIVE_FIXTURE={'execution_wolf':'1/5','execution_other':'4/5','three_value':'1/3','village_win':'7/15'}
