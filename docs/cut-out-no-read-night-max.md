# 5人・profile読取なし証明の接続

診断済みの5人例を、比較専用 `adapt_no_read_night_max_model_a` / `NoReadNightMaxEngine` へ接続した。範囲は初日5人、全員潜伏、W1/S1/H0/M0、初日取得なし、昼max/夜max、full公開設定・偽報告randomのみ。通常rootの対応判定、通常UI、公開設定は変更していない。4人終局夜の入口と昼max/夜均等の入口も従来のまま明示的に分ける。

## 証明を許す二つの条件

構造条件は、初回処刑を外した4人生存・初夜、狼1、狩人なし、霊なし、潜伏占1、公開能力CO/報告なし、元人数5、初日取得なし、自噛みなし。襲撃後の3人昼ではどの処刑も物理的に終局するため、後の夜方針を読む枝がない。guardの公開kernelを読む経路もなく、公開能力報告もない。この境界を満たさない入力は証明を試さず明示拒否する。

その上で `guarded_profile_probe` は旧 `CandidateRules` と同じ完全sourceの候補規則を作り、全本人情報集合・全合法候補を旧 `FixedPublicWolfProfile(stop_on_policy_read=True)` のcommon flowで評価する。各候補はfresh engineを使い、未保護の以前の結果や部分証明をcacheから取り込まない。profile値の利用箇所である `public_night_policies` は最初の読取要求で例外を出す。固定profileの保持は評価cacheのidentityと、この監視されたkernel providerに限られる。候補の現在方針自体は旧規則どおり完全sourceの同値な情報集合・対象へ一緒に適用する。

全候補の値計算が、既存の厳密なchance/terminal計算も含めて完了し、profile読取がない場合だけ、既存 `best_response_profile` で全候補値から最小値・同点均等を求めた完全 `ProfileCertificate` を返す。新しい固定点・解選択規則を追加していない。読取、Pending、予算停止のどれでも selected を返さず、途中の数値を独立証明として採用しない。証明用common flowは既存のreconstruction境界でBoardの二重replayを抑えるが、配役・取得・物理遷移の計算は変えない。

夜方針の証明cacheはrules/strategy、完全公開Board、公開jointと全metadata、公開履歴をキーにする。本人閲覧条件はこの公開証明の入力にしない。成功した完全証明だけを保存し、その中の狼自身の群れ・襲撃履歴の行を取り出す。公開配役重み、世界内秘密履歴混合、物理枝質量を分け、viewerの役職・取得を他人の方針選択へ渡さない。

## 数値と実読取の対照

各公開初夜contextには狼4情報集合、各3合法対象。旧依存分類は理論上2401 profileを数えて1-profile上限で未完了だったが、読取なし証明はその積を展開しない。全12候補の値は村勝率1/3、profile読取0回で、既存の同点均等が得られた。この行は全個人ラベルで評価する元の情報集合maxとも完全一致する。

公開rootは全5処刑が7/15で同点。潜伏占1の本人条件では自己処刑が1/3、他4人が1/2だが、公開の同点方針を本人の秘密で選び直さないため本人評価は7/15。次の本人占い対象2/3/4/5も設定済み方針で各7/15。占い方針を別のmaxへ変更した結果ではない。既存SeerObserverによる介入と、本人取得端点を固定した群の精細化を維持する。

対照は実際の3人・W1/H1/C1・初夜という既存guard経路を使った。構造gateはこれを拒否する。同じ読取監視器で候補評価を行うと、guard/public kernelの最初のprofile読取要求を1回検出して `fixed_public_profile_read` で停止し、数値証明を返さない。人工的な定数返しやprofile読取のmockで対照を作っていない。

## 有限検証と限界

`python -B -m benchmarks.player_match_groups.cut_out_no_read_night_fixture`。公開、本人役職条件＋占い対象介入、実読取対照の3 workerと、既存50＋新規3の53回帰を検証する。完全公開Table/primary/cumulative、本人条件付き処刑Tableと占い対象Table、全選択/翌朝値、物理枝質量、公開/本人の完全joint、独立列挙した取得・死亡・襲撃履歴、同一originの終端読戻しとcache/cold再構成を全個人ラベル参照と比較した。読取対照の拒否と範囲外入力も回帰で固定した。

各run60秒、評価入口25秒、証明probe12秒、全driver300秒、WorkingSet1,500,000,000 bytes。実行済みの有限run中にMorishi側の計測枠調整連絡を受け、追加の速度計測は行っていない。所要時間は予算内完了の記録だけに使い、非競合条件の速度比較として扱わない。

証拠は `benchmarks/player_match_groups/cut-out-no-read-night-max-results.json`、回帰ログは `.artifacts/no-read-night-max-regressions-final.log`。今回の全候補一致は一般の相互依存の解法完成を意味しない。霊あり/初日白/途中CO・報告/複数夜/guard/GJ等の夜maxをこの入口へ拡張せず、実際にprofileを読むケースは拒否する。狩人や7人max、通常UI採用、一般固定点の解選択は残件。公開・push・server変更なし。全project suiteは実行していない。
