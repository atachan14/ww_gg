# 7人既知狩人村の性能・対称性調査

対象feature HEAD21ab4b4。実行コードの大きな設計変更はしていない。入力は市民4・狩人1・狼2、Day1昼、全生存。P1狩人CO＋標準filled条件で真狩人100%、P2～P7は市民2/3・狼1/3となる通常初期Board。初期role worldは15（6人から狼2人）。未知設定は昼max・夜max・護衛uniform・自襲撃なし・連続護衛ありを既存デフォルトとして仮定。

## 実測

標準work250000／20秒、cProfileとtraceを無効にした測定も19.990秒でinformation_set_budget_exceeded。成功値cache6636、action cache16800、wolf policy2545、取得cache4620、day score state164。途中までの数であり、完全探索ノード総数ではない。

同じ入力のcProfile＋trace測定は20.000秒で予算切れ。候補act5181回、action hit233（4.5%）、uncached act4948回、solve1889回、guarded_outcomes2179回。wolf policy cache761件、異なるpublic state45件、初期狼roster15種類。過去襲撃記録の長さ別infoset件数は0夜233、1夜321、2夜207。morningは1296回中1211hit（93.4%）。朝のcacheは効いている一方、候補行と名前違いの継続状態の再利用が弱い。cProfileの累積時間は再帰的に重なるため各項目を足して総時間にしない。

3秒の別サンプルではvalue cache1127件。P1を固定しP2～P7の15通りの交換について、全Board、公開/物理jointのrole masks・質量、scan/guard/attack履歴、取得roster、過去報告を一緒に置換した。入力の15交換すべてで完全状態が不変。配役・hypothesisの列挙順は正規化して比較した。

保存済みkey同士の厳密な交換一致は5948組、接続した同値群は94、ラベル違い重複は1033件（91.7%）、一致群内のvalue不一致は0。既知の交換で結ばれた計測サンプルだけの下限で、全状態の最大圧縮率や実行時間の改善率を表さない。入力周辺確率だけの署名ではなく、private lawを含む計算key全体を比較した。

連続護衛なし＋昼夜maxは0.002秒でguard_no_repeat_max_unimplemented。これは性能の予算切れではなく、現機能が未完成のための明示保留。連続なしの数字を連続ありへ混ぜない。

証拠はtask-6/seven-known-guard-baseline.json、seven-known-guard-profile.json、seven-known-guard-exact-swaps.json。隔離測定スクリプトも同ディレクトリに保存。

## 既存圧縮と未対応の位置

- information_set_forecast.py:128 equivalent_targets は狩人ありで即False。その下にある公開joint置換による代表候補比較を使わず、同値候補もactで評価する。実測1289回の同値照会はこの入口で落ちる。P1は別、P2～P7は初期対称でも現判定はFalse。
- 同:185 renamed_value_key と joint_value_key.py:30 public_variants は狩人ありを除外。既存は1人の公開占い、潜伏ラベル最大4までの制限付き名前置換。初期P2～P7は6ラベルなので、狩人制限を外すだけでもそのまま使えない。
- medium_value_key.py:35 public_descriptor は初期占い／狩人ありを除外。無能力・霊能の対称な公開/本人法則には別の圧縮がある。
- information_set_forecast.py:80 exchangeable は生存狩人の確率質量があると人数のみの再帰を使わない。護衛可能性を捨てる近道を避ける正しい制限で、単に削除しない。
- root_secret_flow.RootSecretEngine は完全秘密履歴の保持を優先し、flow memoと履歴圧縮を無効化している。今回の既存max基準はInformationSetForecast経路で、root計測結果と混同しない。

狼・占いも同じact/solve・取得・朝フローを使うため、役職ごとの画面の問題ではない。狼rosterと自身の攻撃履歴がpolicy cacheのキー、占いの対象関係が名前置換を壊す条件である。占い側には限定された圧縮があるが、潜伏占い・複数夜・狩人混在まで一般化できているわけではない。

## 次タスクの一般改善案

1. CO、生死、個別policy、日付付き公開報告の有向関係、必要な取得/護衛/襲撃履歴、公開joint、物理joint、actor infoset、observer interventionをまとめた置換不変性を判定する。表示値や一行の局所署名の一致では判定しない。
2. 候補行のorbitで代表を評価し、対象IDの写像を戻す。確率枝のorbitでは元の人数・確率多重度を正確に残す。15配役や6ラベルを一律6倍と仮定しない。
3. Scalar/act cacheは正規形keyで再利用し、wolf policyのroster/own historyと選択候補を同じ置換で戻す。秘密を共有させたりworldごとのoracle maxへ変更せず、infoset集約→候補評価→最大化→物理枝の順序を維持する。
4. 既存値・同率均等・本人/公開・報告が別の行に刺さる反例・複数夜・連続あり/なしを比較し、節約ノード数とcache率を測定する。新役職にも同じ一般構造を使う。予算増加より同義枝の圧縮を優先。

順序は現在の狼襲撃max（task-c857928fd4324a51）→代表計算（task-1123468027e5405e）。今回の再現/profileを土台に、一般同値判定・多重度維持・実装検証へ進む。大きな設計変更は原因と改善案の報告後に判断する。

その次は同時行動の相互期待勝率最大化の共通設計。Strategy.seer_positionはunvisited→uniform、guard_positionはuniformのみ、本人Tableの固定位置比較は共有取得lawを変えないため、役職の自動maxとは別。占い×狼、狩人×狼、占い＋狩人＋狼を同じ情報集合・混合選択分布・設定済み継続方針で設計する。敵側が固定policyのときだけ単側maxでよく、双方maxを逐次best responseや相手の現在行動を知るoracleで代用しない。村側役職同士が秘密を共有できる協調プレイヤーと仮定しない。均衡の定義・混合/相関の許可・解法・計算量・複数解選択は設計段階で整理する。先に共通flowの未確定kernelと候補評価の依存問題を解く必要がある。