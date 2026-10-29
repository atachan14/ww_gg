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

その次は同時行動の相互期待勝率最大化の共通設計。Strategy.seer_positionはunvisited→uniform、guard_positionはuniformのみ、本人Tableの固定位置比較は共有取得lawを変えないため、役職の自動maxとは別。占い×狼、狩人×狼、占い＋狩人＋狼を同じ情報集合・混合選択分布・設定済み継続方針で設計する。敵側が固定policyのときだけ単側maxでよく、双方maxを逐次best responseや相手の現在行動を知るoracleで代用しない。村側役職同士が秘密を共有できる協調プレイヤーと仮定しない。均衡の定義・混合/相関の許可・解法・計算量・複数解選択は設計段階で整理する。先に共通flowの未確定kernelと候補評価の依存問題を解く必要がある。計測指標の限定：1,127状態／1,033重複は、連続あり・昼夜max・7人既知狩人の3秒サンプルで、完成したvalue cache key同士を全状態置換して検出した件数。完全探索総ノードでも実装後ベンチマークでもない。代表計算実装による実行時間改善はまだ測定・実証していない。


## 実装：完全情報の名前置換による候補・利得cache

ユーザー承認で①を残件として保留し②を先行。①の79c4297のpublic_continuation_zero_supportおよび一般未知6人max未解決は変更しない。公開ゲートは①②完了後のまま。

exact_renaming.pyは、全Boardフィールド、公開/本人jointの全役職mask・各仮説の確率・scan/guard/attack記録、獲得roster、tracked、observed_prefix、過去公開報告、物理Board、Rules/Strategy、現在候補target、認識済みGuardObserverをまとめて正準化する。色分けは探索候補の削減だけであり、同じ色や表示確率だけで同値と判断せず、最終的に完全なsnapshot同士を比較する。役職や公開/私有履歴の有向関係を同じbijectionで置換する。

対象はInformationSetForecastの狩人を含む既存正常経路のscalar/action cacheと候補同値。狼候補の同値判定にはPUBLIC由来の本人情報集合も含め、公開候補用フックと分離した。利得scalarだけを再利用し、確率枝や配役worldの質量を統合しない。max/tieの選択、元の全行IDと人数、多重度、chance massは従来のflowで保持する。policy cache自体は名前置換しない。

名前置換全数が10000を超える場合、未知のrecord/observer/configuration形の場合は正準化を省略し既存計算へ戻す。上限は人数の決め打ちではなく正準化の計算量制限。正準化中も既存calculation_budgetを確認する。現行方針項目をStrategy全体としてkeyへ含め、新しいplayer-ID付き方針を勝手に対称扱いしない。完全root秘密経路はmemoize_flows=Falseを維持し、①のPendingや支持を圧縮で隠さない。

新規回帰はon/off全Forecast厳密一致（5人、昼夜random、両連続護衛ルール）、max/maxと本人狼配役の厳密一致、非対称配役重みの不統合、狼の秘密襲撃履歴・GJ記録、合法な公開占い報告の有向関係、GuardObserverと本人介入、探索上限時の未圧縮継続。旧NoRepeat maxの未対応Pendingも保持する。既存公開候補フックの互換性を維持。

最初の標準7人測定：off20.000秒でPending、value展開6221/action展開15813。on5.680秒で全Forecast完了・村11/45、value展開400/action展開907、policy cache268。最終ソースの再測定（全回帰と並行中）：off19.994秒でPending、value展開5787/action展開14795、on6.422秒で完了・村11/45、value展開400/action展開907。正準key問い合わせ4090・raw key再利用1282・支持済raw key2808。CPU条件の差を速度倍率の厳密保証には使わない。

非圧縮120秒では全Forecastは未完了。長い非圧縮参照ではP1候補2/15、P2/P3/P4/P5候補各11/45を独立に確認（各未知側候補約113〜117秒）したところで中断。7人の完全on/off Forecast一致を達成したとは記載しない。標準予算切れ→圧縮完了の効果、完了した非圧縮候補の一致、全Forecastの一致を別に記録する。長いoffの再実行は合理的な資源範囲で抑える。検証ログはtask-6/symmetry-seven-comparison.json、symmetry-seven-off-complete.log。

Windows更新前チェックポイント：全562テスト183.422秒成功、再開後の重点12テスト5.944秒成功。最新指示でpushは取り消され、remoteへの変更はゼロ。ブラウザー確認と18801への新コード反映、7人の非圧縮全Forecast比較は未完。①②の公開ゲートは維持して待機する。


## Windows更新後の完了検証

保存HEAD b54b8ceをクリーンな状態から再開。7人の全Forecastを同じ入力・Rules/Strategyでon/off比較し、村勝率、全7候補行、全7のby-dawn値、pending_metricsのすべてがFractionで厳密一致。on6.137937秒、off843.623078秒（完了行ごとのcache保存時間を含む）。on action展開907/value展開400、off action展開611413/value展開254894。offへの比率にはcheckpoint I/O時間も含むため、純粋なCPU速度倍率としては扱わない。

村11/45、P1候補2/15、P2〜P7候補11/45。昼maxは元の6同率候補をすべて保持し各1/6、確率和1。全by-dawnの村/狼値は0。圧縮はchance枝の確率やworld質量を統合せず、scalar/key同値だけを再利用する。

専用18801の空きを確認してPID19100で実装を反映、TOP/HELP HTTP200。ブラウザー制御面は起動直後に終了したため、既存隔離Edge手順（PID20376、専用18802、task-6/post-update-symmetry-edge-profile）を用いた。通常TOPでC4/H1/W2を設定しP1狩人COを公開。昼の11/45、全7行、P1真狩1、市民/狼確率を確認。P2処刑→夜→戻る→再読込の保存表示は厳密一致。夜のP1本人視点では合法護衛P3〜P7の村/狼は11/45・34/45、自護衛P1と死亡P2は空欄。公開へ戻ると襲撃P3〜P7が59/225・166/225へ復元し、本人介入cacheが公開へ混ざらない。各完成行の陣営確率和は1、全7行を保持。

実装の全562テスト183.422秒成功の保存結果と、両護衛ルール・非対称情報・秘密履歴・占い公開報告・max/max・本人狼のon/off回帰を保持。今回の検証でコード変更はなし。②の代表cache実装と検証は完了し、①は一般未知6人の継続maxを共通モデルで解消する残件。①②検証完了までpush/deployは行わない。

証拠：task-6/symmetry-seven-resumed-verify.json（complete_exact_equal=true）、symmetry-seven-final-summary.json、symmetry-browser-consistency-check.json、symmetry-seven-browser*.json/png。非圧縮参照cacheはsymmetry-seven-off-engine.pickleに保存され、再計算は不要。
