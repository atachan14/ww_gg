# SavedOriginと全ラベル枝の接続（実験用）

`SavedCutOutGraph` は正式Model A初期分布を起点に、切り出し型一致グループ方式の全ラベル枝を既存の `SavedOrigin(project_public=False)` → `GeneratedBoard` → `ActionEvidence` → 朝の追加公開recipeへ登録する。対象は4–5人、狼1、狩人なし、均等方針、初日処刑から最初の朝までの公開役職評価。通常UI・既定設定・公開経路は変更していない。

処刑・襲撃は元のラベルを保持し、各Boardの `roles()` から完全な公開/秘密共同分布・物理状態・pastを再構築する。襲撃の本人情報条件と既存方針を用いた観測尤度も再計算する。確率は選ばれた処刑対象に条件付けた枝確率であり、代表クラスの人数分の質量ではない。子の事後分布をoriginに埋め込まず、子で初期配役を再割当しない。初期adapter構築とSavedOrigin一致gateにはそれぞれ正式初期分布の構築費用がある。速度改善は主張しない。

朝recipeは今回新しく加わる報告だけを保持する。古い入力prefixを絶対公開キーとして保存しないため、初期白対象を訂正した際に古い白情報を再適用しない。`corrected` は既存 `BoardData.updated` によりGameData/runtimeを共有した新しい不変入力snapshotを作り、新SavedOrigin・recipe・群・scopeを構築する。旧snapshotは引き続き読める。到達不能な観測は `InvalidatedBranch`、対象外は `UnsupportedPartition` とし、一律補完しない。

`rows()` は実際の `PlayerData` を役職段階だけ生成する。各比較行の共通contextは完全な `ContinuationInputs` と対象の実際のGeneratedBoardを指す。比較は同一context内の同一構成群に限定し、別Board・訂正前後を同一視しない。入力digest・枝観測digest・revisionを含むViewScope/ResultFrameを使用し、行動値・勝率はpendingのままにする。PlayerData本体や通常Tableの生成経路は変更していない。

## 小規模検証

`python -B -m benchmarks.player_match_groups.cut_out_saved_recipes_fixture` で再現。4人終端・5人単独占CO・複数占CO・真偽霊COの合計291本について、保存recipeのBoard全項目、完全な秘密共同分布、past、物理状態、枝確率が前段生成結果と一致した。訂正後の役職変化、古い証拠の非再適用、到達不能枝、異なるBoard間の比較禁止、非memo再構築も確認する。既存BoardFlowと朝処理の回帰テストも実施する。証拠は `cut-out-saved-recipes-results.json` とローカル `.artifacts` のログ。全suiteや重い性能workerは実行しない。

## 残る境界

全CO取消の180対60は、adapterがCO者のみの公開priorを選び潜伏占いの初期取得を省略していたことが原因だった。現在は既存 `prepare_joint` の正式入口選択を先に行い、rootがあればその完全法則を参照のまま保持する。root対象外では従来の固定CO公開priorを維持する。cast/rule/policy変更は引き続き同じ履歴への付替え対象外。

今回の訂正APIは明示的な初期snapshotだけを対象とし、アプリのowned Board graph編集commit・子孫retirement・取消UIには接続していない。生成recipeの子孫は実験用registryで保持する。通常の一時B Board更新フローには変更を加えず、その既存回帰テストで非退行を確認する。owned graphのrevision/archiveを含むアプリ編集への接続は別段階で必要。

勝率評価ループへの登録、私有視点、複数夜、7人、max、狩人への拡張は未実装。現段階は全ラベルの保存入力→生成Board→役職再評価と比較contextの接続までであり、全統合完了ではない。

## 全CO取消の独立対照

4人・5人の取消→再CO→結果訂正→取消を検証。5人では元の60配役それぞれに真占いの合法初回白対象3通りがあり、180秘密状態となる。独立列挙した共同分布は旧正式root入口、修正adapter、SavedOriginと厳密一致する。秘密取得を周辺化すると固定CO公開priorの60配役へ戻り、役職重みの相違ではない。観測済み事後から初期priorを作り直したり、失った候補へ一律質量を足したりしない。保持した初期specの配役数・ルール・方針から既存正式入口を呼び直す。

往復の合計295枝について、群を使わない既存物理・公開処理の全ラベル対照と、共同分布・役職率・物理状態・履歴・条件付き枝massが一致。古い観測descriptorを訂正先へ付け直した場合も、新しい生成結果と一致するか到達不能として無効化する。最初と最後の取消の全枝は完全一致し、旧snapshotは不変。取消解消に通常フローの変更や勝率拡張は不要だった。

再現: `python -B -m benchmarks.player_match_groups.cut_out_cancellation_fixture`。証拠: `cut-out-cancellation-results.json`。以前の291枝証拠はそのcommit時点の記録として残す。
