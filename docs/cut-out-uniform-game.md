# 切り出し群から均等方針の決着評価（独立試作）

`cut_out_uniform_game.evaluate(SavedCutOutGraph(...))` は既存の物理遷移・取得・朝公開・生成Board再構築を通して決着まで評価する比較用entry。通常factory・UI・公開設定・サーバーへは接続していない。4–5人、狼1、狩人0、既存均等方針に限定する。この人数では一夜・最大二度の処刑で決着する。

初期群を、公開死亡・報告の端点、本人の既知役職/結果、狼本人のrosterでのみ細分する。子で対称群を推測したり再結合したりしない。昼は代表の値を群人数/生存人数で、夜は本人rosterごとの群内方針確率の和で集計する。全質量と公開/本人法則をcache keyに含め、異なる条件の値を共有しない。旧全置換canonical key・target交換照合は無効化し、無条件の旧経路fallbackは設けない。

同じSavedOriginを各子のActionEvidence/PublicationEvidenceと本人条件recipeが引き継ぐ。子の役職・取得履歴・攻撃履歴を保持し、子ごとに初期priorを作り直さない。本人秘密はOwnViewで本人の役職と取得結果だけを条件付ける。公共方針は公開法則を読み、本人秘密を行動方針へ渡さない。

対照 `OfficialLabelledEngine` は旧 `InformationSetForecast.solve` の全個人再帰を使い、試作のsolve/groupsを呼ばない。こちらも全置換探索・履歴圧縮を無効化する。共通物理kernelを使う独立した制御フローの対照であり、別実装のゲームルール対照ではない。

公開Tableは既存 `build_public_view` の全行（CO/結果timeline・役職率・合法手・行動値・翌朝値を含む）、本人Tableは既存 `private_api_rows` の全出力を比較する。Forecast全体、代表として実際に評価した全枝の物理確率、子の完全公開/本人共同分布・past・物理Board、生成recipe再構築も厳密一致を確認した。

## 有限計測

再現: `python -B -m benchmarks.player_match_groups.cut_out_uniform_game_fixture`。各ケースは新規プロセスで30秒、計測全体180秒が上限。評価entry自体も25秒まで。今回7ケース合計は 8.828 秒で、重いworker・全suiteは実行していない。別途5回帰テストも成功した。

| ケース | 村勝率 | 切り出し評価 秒 | 全個人評価 秒 | 比率 | プロセスpeak MiB |
|---|---:|---:|---:|---:|---:|
| four-single | 1/4 | 0.0135 | 0.0157 | 1.17 | 33.7 |
| five-single | 7/15 | 0.0906 | 0.1671 | 1.85 | 34.9 |
| latent | 7/15 | 0.3896 | 1.8757 | 4.81 | 56.6 |
| medium | 7/15 | 0.1152 | 0.1315 | 1.14 | 35.9 |
| same-reports | 7/15 | 0.1535 | 0.2679 | 1.74 | 39.5 |
| own-seer | 7/15 | 0.0966 | 0.1713 | 1.77 | 35.4 |
| own-wolf | 7/15 | 0.0404 | 0.0623 | 1.54 | 33.8 |

一回計測であり統計的な速度保証ではない。共通の初期adapter/SavedOrigin準備、Table整形・一致検証、任意の全ラベル共同分布復元は上表の評価時間に含めない。ピークメモリは同一ケース内の両engine・検証・任意復元を含むプロセス全体のWorkingSetで、engine別のメモリ削減は判定できない。

JSONには `cut_out_seconds`（証明済み群の細分・検索、本人rosterの走査を含む）、`law_seconds`（取得・朝生成・子法則再構築）、`label_restore_seconds`（同一群の行動値のラベル復元）、残りの `evaluation_other_seconds` を記録する。法則列挙を消した性能と混同しない。`inclusive_action_seconds` は再帰包含時間なので加算不可。

完全なラベル付き共同分布が必要な費用は別に計測する。`optional_public_generation_seconds` は前段の初期/朝生成、`optional_all_label_joint_restore_seconds` はその初日〜翌朝の全ラベルrecipe登録・roles読戻しであり、勝率solveの必須費用ではない。潜伏例の後者は約1.01秒で、評価短縮を上回る。全終端木を全ラベルで保存する機能ではない。

## 対応境界

max・狩人・7人・複数夜・新たなCO/報告方針・任意の途中Boardからの開始は対象外。入力は既存の限定SavedCutOutGraphに限る。本人情報の支持ゼロ、共通kernelのPending、評価予算切れは明示的なUnsupportedPartitionを返す。途中までのTableや黙った均等置換は返さない。既存の全CO取消→再CO→結果訂正の初期snapshot再構築は前段を使用する。

通常のBoard編集/取消UIへの接続、一般人数・複数夜の切り出し規則、maxの相互最適化は残件。公開していない。証拠は `cut-out-uniform-game-results.json` と `test_cut_out_uniform_game.py`。

6人・二夜については、別の明示入口による[継承検証と総費用](cut-out-two-nights.md)を追加した。一般人数/複数夜への通常接続を意味しない。
