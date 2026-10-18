# 夜maxの依存関係：4人の終局境界と5人の未完了例

## 旧方式が厳密に計算するもの

`wolf_profile_certificate.py` は、完全な公開Board・joint・公開履歴・rules/strategyを一つのsourceとして扱う。狼本人の情報集合は初期群れと本人襲撃履歴から公開jointを条件付けて作り、他人の秘密や閲覧者の本人条件で方針を変えない。

`CandidateRules` は完全sourceの厳密な自己同型で同値な情報集合・対象へ同じ候補規則を適用する。単一worldの最適値を混ぜる処理ではない。候補の評価は固定された完全公開方針profileの下で既存common action flowを通り、設定済み昼方針・取得/報告・公開観測を含む継続勝率を求める。全合法対象の村勝率を最小化し、同率の全対象を均等に選ぶ。`best_response_profile` と候補profileが一致するものだけが認証対象になる。

`ProfileSearch.selected` は認証が一意で完了した場合だけ返る。複数、undefined観測、依存未完了、予算未完了から任意の方針を選ばない。この既存規則は新しい任意混合・均衡選択規則ではない。公開配役重み、世界内秘密混合、物理枝の質量はそれぞれ既存Board/common flowの担当であり、候補profileを独立確率近似へ分解しない。

## 最小4人：移植できた終局依存切断

全員潜伏の4人、W1/S1/H0/M0または1、初日なし/ランダム白、昼max/夜maxを比較専用で追加した。処刑で狼を外すと夜は3人・狼1。自噛みなし・狩人なしなので、狼が選ぶどの合法対象でも2人・狼1となって狼勝利で終局する。将来の公開maxや報告方針を参照しないため、本人情報集合ごとの全襲撃値は村勝率0。同点均等は既存max規則から一意に決まる。均等へ置換したstrategyを用いていない。

旧証明器はこのcontextに理論上27方針を数えるが、`max_profiles=1`・12秒上限で、1完全評価から `unique / policy_independent_scores` を返す。実際の候補値は全て0、本人ごとに2合法対象を各1/2。切り出し型の既存 `wolf_policy` の情報集合別minと完全一致した。旧参照は小さなsourceのCandidateRulesで旧canonical判定を用いる。切り出し本体へ全置換探索や全profile積を移植したわけではない。

`adapt_terminal_night_max_model_a` は4人・全員潜伏に閉じ、既存の昼max/夜均等入口から明示的に分けた。`TerminalNightMaxEngine` は3人夜・W1・H0・自噛みなしの境界を確認した上で既存maxを呼ぶ。通常root eligibility、通常UI、公開設定は変更していない。本人の現在の占い対象介入も既存 `SeerObserver` を用い、元の対象域・未訪問優先と本人の既知取得だけで合法手を作る。

全員潜伏の公開値は1/4。初日白3を持つ占1本人ではP2/P4処刑値が1/2、P1/P3が0だが、公開の昼同点方針を選び直さないため本人評価は1/4。初夜終局でも、取得と襲撃履歴を含む終端jointの読戻しを省略してよいとは扱わない。

## 最小5人：何が未接続か

5人・全員潜伏・W1/S1/H0/M0・初日なしの、初回処刑を外した4人夜を保存した。同じ旧証明器を `max_profiles=1`・12秒で一度だけ診断すると、理論上2401方針、`budget_unfinished / dependency_feedback_limit / dependency_elimination`。完全profile評価0、profile work消費1、一意の認証なし、数値方針のcache設置なしだった。

4人夜からは襲撃後に3人昼が続くため、旧compilerは保守的な依存群として分類する。ただしこの最小例では、追加の実行時診断により実際のprofile依存がないことが分かった。`FixedPublicWolfProfile(stop_on_policy_read=True)` で旧CandidateRulesと同じ候補規則を作り、4本人情報集合の全12合法候補をcommon flowで評価したところ、すべて村勝率1/3・profile読取0回だった。読取が起きれば診断を中断するため、任意profileを仮定して値を採用した処理ではない。

従って `dependency_feedback_limit` はこの例では実際の相互依存や複数解の証拠ではなく、非終局夜を独立性probeより先に保守的な依存compilerへ送る旧実装の制約である。切り出し型へ残る接続点は、このような全候補・全確率枝の読取なし証明を、完全sourceと候補規則を保持したまま独立スコア証明へ取り込む部分である。今回の実装採用はより狭い4人終局境界に限定した。5人の診断値からroot全体の夜max対応を宣言していない。

この診断は、5人で解がない・複数ある・新仕様が必要と証明したものではない。上限内では既存の一意性/定義域の証明が未完了という意味である。2401方針を実行していない。上限を広げず、任意profileやworld別最適化、独立確率で数値を埋めない。将来multiple/undefinedが具体的に得られた場合も、現在の既存契約では数値を選べず、その証拠と必要な仕様判断を報告する。

## 有限検証

`python -B -m benchmarks.player_match_groups.cut_out_terminal_night_fixture`。

4比較（M0初日なし公開、M1初日白の公開・本人役職のみ・本人白結果）と5人診断を各新規プロセス60秒、全体300秒、WorkingSet1,500,000,000 bytesで制限する。各評価は25秒、旧認証呼び出しは12秒・profile work上限1。大量profile探索を行わない。

完全な公開Table/primary/cumulative、本人条件付き処刑Tableと占い対象Table、全選択・翌朝値、物理枝質量、公開/本人の完全joint・取得/死亡/襲撃履歴、同一originからの終端再構成、cache/cold初期読戻しを全個人ラベル参照および独立列挙と照合する。旧一意認証の全行と切り出し夜方針も一致させる。既存47回帰を維持し、新規3回帰を追加。

証拠は `benchmarks/player_match_groups/cut-out-terminal-night-max-results.json`、回帰ログは `.artifacts/terminal-night-max-regressions-final.log`。5人の一般夜max、途中CO/報告変更、狩人/GJ、7人maxは残件。通常UI・公開・push・サーバー変更なし。全project suiteは実行していない。

最終実測は4比較＋5人診断＋50回帰で42.500秒。各新規プロセスの時間とピークWorkingSetは保存JSONに記録した。認証は各公開contextのprofile work上限1を維持した。
