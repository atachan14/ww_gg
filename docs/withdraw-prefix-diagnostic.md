# 撤回後full-disclosure Pendingの最小診断

最小再現は4人（狼1・占い1・狩人/霊なし）、初日P1占CO＋P3白、P2処刑後の夜BoardでCOと報告をwithdrawする例。現在有効なCO/報告は空になるが、標準SavedOriginは `full_disclosure_truth_not_conditioned` になる。6人や二夜目は必要ない。

## 原因と既存の意味

`public_log_changes.project_changes` は現在有効な宣言内容だけを入力へ投影する。一方、`result_disclosure.snapshot` は各過去Boardで当時のfull-disclosure義務と報告の存在を判定する。`root_secret_flow.observe_root_snapshot` のpastには現在有効な具体的報告しか入らない。再生の `root_scope` がpastを「報告の存在」の証拠としても要求するため、既に過去公開義務を満たした真占いの世界を重複ガードで止めていた。

既存回帰 `test_closed_full_co_omission_survives_later_withdrawal` は、閉じた過去Boardで未報告だったCOの偽判定を後日の撤回で救済しないことを要求する。`test_active_input_target_only_then_generated_true_history_is_preserved` と実装のprovenanceコメントは、退役した結果内容を実取得として固定しないことを要求する。したがって「報告があったという存在」と「現在有効な具体的内容」は別である。

過去情報をすべて消す変更は前者の期待を壊し、退役した対象/色を真の取得へ固定する変更は後者を壊す。今回、そのどちらも選んでいない。現在の公開配役oracleも変更していない。

## 明示フラグだけの局所修正

`replay_root_secrets(..., _historical_disclosure_proof=True)` は、明示的にfull-observedが記録された過去stepについて、既存snapshotが持つ `(報告者, 取得日)` の存在証明だけをstepのガードへ渡す。対象/色、fake報告からの実取得、未知世界への一律質量は追加しない。取得履歴は元の配役・ルール・均等取得から生成する。

4人例では公開狼率 P1=3/5・P3=P4=1/5 を旧oracleのまま保持し、公開/物理jointの10状態が独立列挙と一致した。P1真占いの初回対象は2/3/4を支持し、旧P3白へ固定していない。現在のpastは空のまま。過去に報告がなかった対照例ではP1狼率1を維持し、真占いの救済は起こらない。6人二行動例も116状態で独立列挙と一致し、既存夜の攻撃記録を保持した。

## 対応範囲と標準入口

**標準入口は未切替。** フラグ既定値はFalseで、通常SavedOrigin、既存6人registry、通常UI/公開の動作は変更していない。既存23回帰にはこの標準Pendingそのものを期待する既知障害のテストがあるため、それを黙って成功期待へ書き換えなかった。旧23本はファイルも期待値も無変更で成功した。

今回完成したのは、最小再現・原因の特定・既存意味に沿った局所修正のopt-in検証。標準Pendingを実際に解消するには、入口でこの証明経路を有効化し、既知障害を固定していた回帰を「旧既定値の再現」と「新入口の成功」へ明示的に移行する段階が残る。現時点で標準経路が直ったとは報告しない。

公開内容を永続した事実として将来も必ず記憶させたい、あるいは閉じた未報告義務も後日取消で消したい場合は別の仕様変更になり、今回の旧oracle維持とは両立しない。その選択は行っていない。

## 有限検証

再現: `python -B -m benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture`。

既存23＋新規3＋既存意味を固定する3＝29テスト成功。各run30秒・全体300秒・WorkingSet1.5GB停止。今回 18.125秒、最大peak 53.7MiB。重いworker・全suiteなし。証拠は `withdraw-prefix-results.json` と `.artifacts/withdraw-prefix-final.log`。修正と診断は独立commitにまとめ、通常UI/公開変更なしで区切る。
