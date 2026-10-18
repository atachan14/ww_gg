# 4〜5人比較経路の統合checkpoint

数値コードの基準は `c4fb959`。今回の変更は検証runner、見直した計画、結果・文書のみ。通常UIへの公開、サーバー変更、push/deployは行っていない。

## 16件の統合回帰

構造レビュー計画のgate8件を維持し、coreの6/7人専用3件を「再帰した霊能報告群」「初期占いCO/報告の再帰群」「報告編集・取消・cache再構築」に入れ替えた。6/7人の対応範囲を広げる変更ではない。

16件すべて成功。正しさsuite61.344秒、下記の別計測を含むdriver全体65.094秒。各worker60秒・全体270秒・PeakWorkingSet1.5GBの制限内。最大worker38.169秒、最大PeakWorkingSet155,992,064 bytes。

新方式の4/5人評価区間を3,852回監視し、その内部の再帰評価・候補値評価・cold replayまで、旧canonical、旧CandidateRules、初期群からの再構築はすべて0回。実際に呼ぶと失敗する監視であり、0の固定メタデータだけを検査したものではない。独立した旧参照・意図的なH1 read-controlは監視区間の外に置いた。scopeのみを検査するselectorなど、各workerの監視区間が0回である場合も結果JSONにそのまま記録している。

Table、公開/本人joint、物理枝と質量、候補分布・報告の同点、本人秘密/将来占い、SavedOriginとcold再読込、明示unsupported、既存の報告編集・取消/cache再構築を関連テストで確認。旧参照は名前付き `OfficialLabelledEngine` と明示オラクルであり、新方式の不足時に暗黙で呼ぶfallbackではない。最初のrunnerは既存テストの直下import用path不足で停止したため、pathを設定後に16件を最初から実行している。

## 正しさsuiteとは分離したend-to-end計測

以下は各方式を別の新規Pythonプロセスで1回ずつ実行した値。共通の比較入口で初期priorを構築し、公開Forecast（root全候補とhorizon込み）、Table、指定した最初の死亡1枝のcold復元まで実行した。全枝の検証オラクルは含まない。正しさ用mock監視も計測中は無効。初期joint、Forecast、Table、1枝の公開/本人joint・質量・physical carrierのfingerprintは各組で完全一致した。

| 代表ケース | 新方式プロセス全体 | 旧厳密参照プロセス全体 | 新方式Forecast | 旧厳密参照Forecast |
|---|---:|---:|---:|---:|
| 4人均等 | 0.437秒 | 0.422秒 | 0.01649秒 | 0.01703秒 |
| 5人占いCO max | 0.609秒 | 0.625秒 | 0.18016秒 | 0.20086秒 |
| 5人霊能報告max | 0.829秒 | 0.796秒 | 0.41789秒 | 0.38382秒 |

プロセス全体は親から見た起動→結果出力・終了のwall timeで、指紋生成などの出力診断も含む。段階別の値はmodule開始から1枝復元終了までで、起動/import、初期prior、Forecast、Table、1枝復元をJSONに分離している。旧厳密参照は全ラベルを評価する同じ比較入口であり、過去の通常UIそのものを起動した測定ではない。

単発の軽量CLIサンプルから一律のend-to-end高速化は確認できない。61.344秒のsuite時間は独立参照・全枝検証・cold照合を含み、製品の応答時間ではない。大きな白jointの速度測定、反復分布、重いaggregate、全project suiteは実行していない。

## 現在の適用範囲と残件

初期Model Aから発行された既存4/5人比較経路で、公開群と本人評価群を共通の取得・死亡・公開報告の子へ継承する。初期CO/報告の保証を保持し、子では新しい観測の固定点だけを分割する。対応済み入口の均等/max設定・合法手・初期白と秘密履歴混合・公開重み/物理枝質量の区別を維持する。

未設定の将来CO、未知のsource/observer、保証できない遷移はunsupported。任意の途中Board・新CO方針を新たに対応させたものではない。6/7人の群経路は今回対象外。旧canonical自体を全projectから削除したという主張でもない。

初期jointの列挙、必要な候補値の厳密評価（fresh評価器を含む）、白jointの全支持検証は残る。群の保証は継続方針の値比較を不要にするものではない。通常UI接続・本来の広い入力/編集フローへの採用・専用サーバー確認・全project検証は別工程。今回の数値コードを一区切りとして保持し、次の重い測定や公開には進めていない。

計画: `benchmarks/player_match_groups/integration-review-plan.json`。実測・各selectorの監視値・段階別時間・ソースSHA256: `benchmarks/player_match_groups/integration-checkpoint-results.json`。詳細log: `.artifacts/integration-checkpoint-final.log`。
