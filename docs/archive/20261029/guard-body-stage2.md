# 狩人本体接続・段階2

ユーザー承認範囲は狩人1人、自己護衛なし、連続護衛あり、護衛成功通知なし。

`Rules.allow_repeat_guard=True` は Game のルールであり Strategy には入れない。新規 Game に保存し、旧保存データは Rules の既定値で補う。既存 GameConfig のルール読取りと draft でも保持する。False の型は保存できるが、合法手生成は未対応として明示的に拒否する。将来の連続護衛なしは `guard_targets(board, actor, rules, previous)` で直前の私的護衛先を用いる合法手制約として追加する。False を暗黙に True として実行しない。画面からの切替はまだ追加していない。

`guard_night.resolve_fixed_guard_night` は実際の Board を受け取り、共通 `action_flow.resolve_action` と NightFrame を使う。選択済み襲撃先に依存せず、事前固定された護衛 intent を取得する。stage1 の死亡効果を一般夜に共通化し、terminal preflight を無効にして護衛後の生存者から勝敗を判定する。成功なら死亡履歴を増やさず翌昼へ進み、失敗なら夜死亡を追加する。死亡した狩人もその夜の固定護衛を実行する。公開 Board・outcome.context に私的護衛先や護衛成功通知は追加しない。観測される無死亡自体は隠さない。

この入口は単一の確定役職世界限定。公開分布の事後推論として使わない。公開 forecast、閲覧用秘密入力、公開進行フォームへの登録は保留。現行 public forecast の狩人能力なしという既存限定も変更していない。

次に必要な判断は狩人の護衛方針（どの情報集合でどの合法先を選び、同率をどう扱うか）。襲撃先を見て護衛を選ぶ代用は不可。護衛成功の個別通知を持たせない前提で、無死亡の公開観測・狼自身の襲撃履歴・本人の護衛履歴を分離した分布更新と保持が次の作業になる。既存公開 dawn API の無死亡拒否も、その更新を用意してから接続する。複数狩人、自己護衛は範囲外。

テストは Game ルールの移行・保存・Strategy との分離、初夜成功、翌夜と反復護衛、狩人自身の死亡、襲撃なら終局となる夜の護衛、無死亡時の公開履歴と私的通知の不在、自己護衛・不確定世界・自己襲撃ルール違反の拒否を確認する。

ローカルのみ。push・公開デプロイなし。

実測: 全体 `python -m unittest discover -s tests` 439件、101.116秒、成功。狩人2モジュール focused 10件、0.004秒、成功。`git diff --check` 成功。実画面は機能接続を保留しているため変更なし。確認入口は `werewolf.guard_night.resolve_fixed_guard_night`、実行例と境界条件は `tests/test_guard_night.py`。
