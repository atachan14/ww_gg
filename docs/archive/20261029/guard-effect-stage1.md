# 狩人：確定世界・単一夜の内部効果

親からの今回の承認範囲で、一人の生存確定狩人・初回夜・非自護衛の生存対象・明示した単一襲撃を処理する純粋関数を追加した。`guard_effect.resolve_first_guard`は護衛一致時にその襲撃由来の一死亡だけを取り消す。不一致および狩本人への襲撃はその襲撃死を保持する。他の死亡原因は同じ人への死亡も含め全て保持し、生存者一覧だけは重複なく更新する。別原因の発動規則や時刻は計算しない。

入力は完全なrole tuple、死亡前alive tuple、immutable GuardIntent(night,actor,target)、選択済みattack target、別原因DeathCauseのtuple。結果は内部物理事実としてdeaths/survivors/prevented_attack。これは本人や狼が成功を知る仕様ではなく、全体を公開ログへserializeしてはならない。襲撃対象のゲーム上の選択・合法性は呼出側の契約であり、この関数は方策を選ばない。

`resolve_guard_frame`はNightFrameの取得後payload `after`から護衛指定を読む明示呼出用adapter。既定のInformationSetActionPolicyやpublic facadeへ登録していない。Boardの進行・勝敗・GJ観測のposterior/累積・UI勝率には接続しない。

自己護衛、連続護衛、複数狩、初回以外、公開/本人/狼の成功情報と方策は対象外。今回の一致取消を全ゲームの最終ルールにしない。既存の死体なし観測は記録のみ・進行未対応のまま。偽占い共同法則も変更しない。

検証：護衛5テスト（不正入力の複数subtestsを含む）成功。全434テスト成功、100.215秒。追加した型/不正frame検証は同じ専用5テストで再確認。入力非破壊・同一入力の決定性・取得前ではなく取得後intentの使用を検査。画面HTML/JS/CSS、既定値、公開評価は変更なし。ローカルのみ。
