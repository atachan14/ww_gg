# 実報告のある霊CO・偽報告maxの接続

比較専用 `adapt_active_report_max_model_a` / `ActiveReportMaxEngine` を追加した。4/5人、W1/M1/S1/H0、霊CO1/2・他は潜伏、初日なし/ランダム白、既存の昼max/夜max/偽報告maxに限定する。CO配置は正式condition_claimsから生成し、初期秘密は正式prepare_root_secretsで生成する。新しいCOルール、報告色の合法性、偽占い方針や相互最適化規則を追加していない。通常UIの入口は変更しない。

## 共通フローでの候補選択

報告の選択自体は `InformationSetForecast.generate_morning` 一箇所のまま。比較用の記録hook `record_report_choices` は候補identity・期待値・選択重みを保存するだけで、通常はno-op。各候補は既存ReportAction.fake_colorsという全潜在偽CO位置への条件付き指示で識別する。worldごとの最良色を足す処理にせず、正式report_flowで完全な公開観測枝を作ってから公開継続値を評価する。最小値の全候補を均等選択し、その指示確率と各観測確率を共通merge処理で掛け合わせる。

基準の5人・処刑3/襲撃4の合法なcounterfactual branchでは、4指示WW/WB/BW/BBの村継続値が順に1/2,1,1,1となり、WWを重み1で選ぶ。真霊の色は実役職と処刑結果から決まり、fake_colorsに書かれた別色で真霊を嘘つきに変えない。

霊COの片方が死亡し狼位置が公開で確定した枝では、残った偽霊の白/黒指示がともに村勝率1。既存どおり各1/2で選ぶ。悪い候補・非選択候補もreport_actionsから消さず、全候補の明示recipeを再構成できることを検証する。

初期5人の公開昼方針は霊CO1/2が同点でroot値1、他3人のcounterfactual処刑値は各1/2。4人では1/2が同点でroot値1/2、他2人の処刑値は0。4人の初夜は物理終局するので、実報告が発生したと誤記録しない。4候補が現れる5人の処刑3/襲撃4は完全Tableの合法なcounterfactual評価であり、rootのmax方針をその悪い選択へ変えた例ではない。

## 夜方針の証明と情報の分離

各夜は構造条件（初回処刑後、3/4人生存、W1/H0、固定2霊CO、S1潜伏、初期snapshotの履歴）を確認する。さらに既存FixedPublicWolfProfileの全本人情報集合・全合法候補を読取禁止で評価し、profile読取なしの完全証明が得られた場合だけ夜方針を保存する。証明が未完了・読取ありならPendingのままにする。今回の報告処理がある例でも、襲撃後は3人昼の終局判断なので、この限定sourceでは既存報告minを含めた全候補評価がprofileを読まずに完了した。

証明は完全な公開Board/joint/履歴とrules/strategyをキーにし、viewerの私的役職・結果を方針へ混ぜない。報告候補のscoreも公開Qだけから計算する。選択された公開観測を本人Pへ適用する際は、共通observer_report_weightsで元の秘密履歴混合と物理質量を引き継ぐ。

具体的に、潜伏占3が初日白1を持つ本人条件では狼2を知る。両霊が白報告をした後も公開Qには狼1/2が残り、公開の処刑方針は1/2の均等。本人Pは狼2だけを支持するが、共有方針での本人値は1/2のままで、本人だけの最大値1へ選び直さない。このprivate posteriorとcold再構成を独立列挙と照合した。

## 完全な候補・観測・履歴照合

全個人ラベルの元の情報集合forecastを参照とし、完全Table/primary/cumulative、本人条件付き処刑Table、現在の占い対象介入、全選択・翌朝値、物理枝質量、公開/本人joint、取得・死亡・狼襲撃履歴を一致させた。

報告候補はformal report_actionsとのidentity一致を確認し、指示ごとの全outcome確率と公開後jointを、独立した初期配役/秘密列挙と履歴進行・真霊/偽霊の色判定から比較する。候補の数値が一致するだけでは済ませず、各指示・各outcomeについてMediumInstructionEvidenceを明示構成し、非採用の指示も含めて同じ保存originからcache/coldで読戻す。単に同じ公開posteriorに合流してstate cacheで共有されたことを、候補の同一性と混同しない。

最終の5人初日白・本人詳細ケースでは、7報告frame、4候補の基準3箇所、2候補同点4箇所、全29候補outcomeの明示cold recipe、本人の公開後posterior6箇所を照合した。指示色・候補値・採用重み・元の死亡履歴は証拠JSONに保存した。

## 5人M1・初日白の入口制限の切り分け

全潜伏5人・市民2/霊1/占1/狼1・初日白は、初期180秘密状態、処刑1を外した初夜で144秘密状態になる。従来の読取なしentryはM0/初日なしという構造gateで拒否する。しかし実際の完全contextを三maxで全12襲撃候補に渡した読取禁止probeは、全候補値1/3・profile読取0・完全独立証明で完了した。

従ってこの具体contextの停止理由は適用制限であり、実際のprofile依存や相互依存を示すものではない。独立を仮定して通した診断ではない。この結果だけで他のCO・履歴・人数へ一般化せず、全潜伏の一般M1/初日白entryは今回拡張しない。今回接続した2霊COのscopeと区別する。実読取が起きる3人狩人ありの拒否対照は既存回帰に維持している。

## 検証と残件

`python -B -m benchmarks.player_match_groups.cut_out_active_report_fixture`。11:29 UTC以降に、4/5人・初日なし/白・公開/本人の4比較とM1白依存診断を有限実行した。既存56＋新規3の59回帰が成功。報告selectorを正式共通フローの記録hookへ整理した後、対象9件と詳細本人ケースを軽く再検証した。

各worker60秒、評価25秒、profile probe12秒、全driver300秒、WorkingSet1,500,000,000 bytes。最終run中にMorishiの保存/GC計測連絡を受け、既存runを完了後はコード確認と軽い対象回帰だけを実施。所要時間は予算確認だけに使い、絶対速度比較を行っていない。

証拠: `benchmarks/player_match_groups/cut-out-active-report-max-results.json`。ログ: `.artifacts/active-report-max-regressions-final.log`、`.artifacts/active-report-shared-hook-final.log`。通常UI・公開・push・サーバー変更なし。全project suiteは未実行。一般の途中CO変更、複数夜、狩人/GJ、7人max、一般相互依存の解選択は残件。
