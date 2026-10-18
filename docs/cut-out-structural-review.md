# 切り出し型の構造レビューと統合回帰計画

レビュー基点: ffadaa4。今回は新機能・数値コードを変更せず、実装・既存証拠・テストselectorを静的に確認した。重いaggregateも新しい速度測定も実行していない。

## 結論

初期に構造から群を作り、閉じた観測でその部分群へ切り出す核は存在する。通常の代表action評価も全置換照合を無効にしている。一方、whole-gameは子に群状態を一貫して持ち回す形まで統一されておらず、maxの安全証明では旧canonical照合とfreshな全候補評価を実行時に呼ぶ。本来の「更新で切り出すだけ・追加照合を増やさない」という狙いは未達。現状は正確性を限定scopeで確認した比較実装で、通常UIへ採用する完成形ではない。

## 群の正しさと方針証明を分ける

**群の正しさ**は、完全な入力law・観測・物理遷移・設定済み方針を保つ位置の交換についての主張。`ConstructiveCutOutGroups._refine_groups` は親blockを観測ラベルで分割し、決してmergeしない。CO、報告、死亡、本人条件の閉じたevent言語に対する構造保証であり、更新のたびに旧全lawから対称性を探索していない。テスト側の全joint swap照合はこの保証の回帰であって、通常評価の必須計算ではない。

**方針の証明/最適化**は、その同じ情報集合の下で設定済み継続値を比較し、max/minと同点均等を選ぶこと。群が正しいだけでは、異なる軌道のどれが最善かは分からない。逆に、全12候補の値が一致したことだけでは群の正しさを証明しない。未知の他人秘密は本人情報集合内で混合してから最適化する必要がある。

## 実装の現在地

| 処理 | 現状 | 本来の狙いとの差 |
|---|---|---|
| 初期群 | ModelAInitialGroupsが正式入力/初期lawを生成し、CO/報告から構造的にblockを作る | 群構築は達成。ただし配役・秘密law自体は全列挙のまま |
| 通常更新 | CutOutUniformEngine.groupsがroot群へ、履歴/報告/本人位置のpoint_fixを適用しfixed集合でcache | 全law照合はしないが、毎回履歴を読みroot群から制限する。子へ群状態を持ち回す一貫した増分更新ではない |
| 6人registry | 保存入力から正式にrootを再構築し、初期群へ公開履歴とlog位置を固定 | 入力更新は新しいsnapshot/root。全編集を差分group更新だけで処理してはいない |
| 均等評価 | 群の代表だけをaction_flowへ渡し、人数/方針質量を掛ける | 実際の評価削減。ただし各代表のjoint取得/物理枝は完全lawを処理する |
| max昼 | 元のInformationSetForecast.solve/day_scoresを使い、actだけを代表cacheへ接続 | ラベルを走査する制御は残る。群内valueは共有するが方針選択全体の群化ではない |
| max夜の読取なし | 各公開sourceで構造gate、全支持検証、旧CandidateRules、全候補probe、完全certificate cache | 安全確認と最適化が旧評価経路に依存。初期群からの候補軌道証明へ未接続 |
| ラベル読戻し | scalarは代表値を返す。個別joint/履歴はSavedOriginとrecipeで必要時に再構成 | 全終端の復元を製品計算ごとに行う必要はない。比較fixtureは意図的に全枝を読む |

`CutOutMaxEngine.groups` は現在のSeerObserverのactor/対象/既知取得端点も固定する。初期本人viewの位置は公開ランキングでも保守的に固定するため、値へ秘密を漏らす形ではないが、public sourceを必要以上に細かく分割するコストは残る。

## maxの「全12候補再証明」は追加照合か

**現状は追加の旧経路を持ち込んでいる。** 白jointでは公開sourceごとに48配役/144秘密を走査し、その後CandidateRulesが各情報集合・対象pairへ旧canonical_keyを呼ぶ。canonicalは色分割後のblock置換、対称性刈込、最大10,000写像の安全上限を持つ。常にn!を全展開するわけではないが、初期に保持した群の証明を再利用せず、完全sourceをまた分類する処理である。

さらにguarded_profile_probeは4本人集合×3合法対象についてfreshなFixedPublicWolfProfileを作り、旧common evaluatorで値を求める。CandidateRulesが同じ軌道と認めたpair間でも、このprobeでは値を共有していない。profile全2401通りを展開していない点は維持しているが、全12候補の旧評価は残る。

この12値は証明だけの捨て値ではなく、実際の夜方針の選択にも使っている。したがって「最適化に候補値が要る」部分まで不要とは言えない。ただし現在は群内で同じ値を繰り返し求め、選択後の物理/本人P評価では別の切り出しengineでも再計算する。公開P=Qの同一contextは共有余地がある一方、本人Pが違う場合へ公開scoreを転用してはいけない。

群の正しさのために全12候補再評価が必須なのではない。将来は、生成時から継承した群/遷移保証と、閉じたphaseのprofile非依存保証を持ち、非同値の候補軌道の値だけを共通評価で計算する構造が必要。先に証明を運べる構造を作らず、今の監視や全支持gateを削除する変更は不可。

## 旧全個人・fallbackの区別

| 経路 | 実行場所/意味 |
|---|---|
| OfficialLabelledEngine | `official_reference=True`を明示した比較fixture。通常の失敗から自動で呼ぶfallbackではない |
| FixedPublicWolfProfile | NoRead/白joint/実報告maxのruntime証明内。旧full-source evaluatorへの明示依存であり、テスト専用ではない |
| CandidateRulesのcanonical不成立 | identity-actionへ保守的に分ける。共有を減らすだけで近似値を返さない |
| 新entryのscope/読取/予算失敗 | Pending/UnsupportedPartition。randomへの置換、部分certificate採用、欠けた秘密の一律補完はない |
| 正式root/prior選択 | 既存prepare_joint/public_priorの意味に従う。独立entryの失敗を旧forecastへ隠れて渡す処理ではない |
| 通常UI | まだ既存経路。比較entryの採用も、unsupported時の新しい自動routingも未実装 |

レビューしたadmitted scope内に、新しい不正確な数値fallbackや未承認のCO/報告/解選択規則は見つからなかった。これは一般入力の正確性保証ではない。特にSavedCutOutGraph.correctedは従来のuniform adapterへ戻るため、maxの編集/取消を新entryへ継ぐ機能ではなく、通常は明示的なscope拒否になる。

## コストについて分かること・未計測のこと

既存白joint証拠の公開ケースは、主engineの代表action15回、全ラベル参照372回。ただし主engineの15回には、5公開source×12候補=60回の旧probeのトップレベル呼出しと、その内部評価が含まれない。generator_checks=0や主engineのcanonical無効化を、max全経路で追加照合ゼロという意味に使えない。

同じ保存runの主評価totalは3.839秒、群の切り出し0.000429秒、主engine law0.223秒、key0.0146秒、未分類other3.594秒。証明内のcanonical、旧law計算、certificate key等はotherへ入る。群分割そのものが主な負担ではないことは分かるが、otherを全部canonical又は全部value評価と断定できない。正確な支配率を判断するには、次の計測でsupport scan、canonical呼出し/写像/class数、probe値計算、certificate cache、主grouped評価を別々に計る必要がある。

比較用RecordedPolicyはoutcome/project履歴を通常の比較entryでも記録するため、その保持コストも製品用の最小構成とは別物。UI前には必要なimmutable recipe/DAGを保ったまま監査ログを分離する必要がある。

workerの15.391秒や詳細本人36.234秒は、旧参照・独立列挙・cold読戻し・検査用の追加evaluateも含む。247.063秒は8ケースと62回帰を含むdriver全体で、1回のforecast時間ではない。今回は既存記録を読むだけで新しい速度計測はしていない。

## 適用範囲と明示未対応

| 比較scope | 対応済みの有限範囲 | 未対応/注意 |
|---|---|---|
| 4/5均等 | 初期Model AのS1/2・M0/1/H0、保存recipe、公開/本人の列挙済みケース | 初期factoryの広さを全S2履歴/一般UI対応と同一視しない |
| 6人均等 | S1/M0/1、二夜joint、限定snapshot編集/CO・報告取消とregistry | 一般夜編集、max、狩人なし |
| 7人均等 | 既知狼・S1/M0/初日なし・秘密支持最大6の最小例 | 一般7人やmaxではない |
| max真占CO | 4/5・真占1CO/白3・M0/1、昼max、夜random/max | 途中CO変更/一般castなし |
| 潜伏昼max | 4/5・S1/M0/1・初日なし/白、夜random | 一般夜maxへ自動拡張しない |
| 終局夜max | 4人全潜伏・S1/M0/1・初日なし/白 | H0で初夜終局する境界のみ |
| NoRead夜max | 5人全潜伏・S1/M0/初日なし | 全候補読取なしの閉scope |
| 白joint夜max | 5人全潜伏・W1/M1/S1/H0・初日白 | 48配役/144初夜秘密の全支持gate。CO/履歴変化は別scope |
| 実報告max | 4/5・霊CO1/2・M1/S1/H0・初日なし/白 | 既存霊偽報告minのみ。4人では実報告前に終局 |

fake_reports=maxは現行の霊報告選択。fake_seer_policyは別の非矛盾優先/均等設定のままで、最適CO・新しい偽占いmax・一般相互最適化を追加していない。狩人/GJ、複数maxの一般固定点/解選択、一般の過去Board編集/取消は未対応として扱う。

## 通常UI接続前の前提

1. scope registryを一箇所で識別し、対応外は従来経路/Pendingへ明示routingする。複数boolean入口の暗黙合成をUIへ露出しない。
2. 生成されたsourceと共に群・scope witnessを子へ渡す。新しいCO/観測で構造的にrefineし、失効時は正しく再構築する。現在のroot point_fixだけで任意のCO変更を処理しない。
3. 公開証明/方針を同一公開source間で共有できる設計と、本人P/observer/物理枝の厳密な分離を保つ。player行ごとにfresh engineで60旧候補を再評価する設計を採用しない。
4. SavedOrigin・revision・編集/取消・cache失効・累積値・現在介入と通常Tableの意味を統合する。初期snapshotの累積値試験だけを途中Boardへ流用しない。
5. 次回計測でproof/実評価/検証用oracleのコストを分離する。群の証明と方針最適化の代替構造が確立するまで安全gateは残す。
6. 代表統合回帰、既存62件、別枠の全project suite、専用サーバー所有元確認後のHTTP/UI確認が必要。今回UI接続やサーバー操作は行わない。

## 統合回帰計画（未実行）

機械可読計画: `benchmarks/player_match_groups/integration-review-plan.json`。16 named selectorと既存26 request/62件が実在することだけASTで確認済み。

| 案 | 内容 | 上限/所要の見積もり |
|---|---|---|
| gate smoke | scope・支持欠落・実profile読取拒否・不可能本人条件・不達recipeの8件 | 90秒枠、概算5–25秒 |
| 代表統合 | 全ラベルrecipe、6人編集/取消、本人max共有、実報告joint、白joint、7人最小の8件 | 180秒枠、概算60–120秒 |
| 既存62のみ | 最新JSONの26 worker request。8追加ケースmainを重ねない | 単独240秒枠、概算90–150秒。保存logのunit時間合計76.705秒＋起動等が根拠 |
| 白対象追加matrix | 対象2/4/5の条件付きTable/履歴 | 必要な変更時だけ別枠120秒。過去3ケース合計約68秒 |
| 全project suite | UI採用前の別window | 過去の旧commit実績約1033秒。現HEAD未計測、5分内と約束しない。別枠1800秒案 |

最初はsmoke＋代表統合（合計270秒cap）か、既存62単独のどちらかを選ぶ。全driverを足し合わせるaggregateはまだ走らせない。5分枠の各案はworker60秒・WorkingSet1.5GB、計画全体300秒を継承する。全projectはこのworker60秒の枠では実行できず、別の時間/RSS監視を持つ別予算・別枠の案であり、このreviewでは実行しない。
