# 狩人未確定・狼襲撃maxの接続調査

HEAD149a302の既存部品を調査。狩人は設定済み均等、狼のみ襲撃max、昼は設定済み方針。相互最大化、複数狩人、新しいCO/報告最適化は対象外。

既存の InformationSetForecast.wolf_policy は公開jointlawを WolfInformation（初期狼配役、自身の襲撃履歴）で条件付け、候補の村勝率を平均してからminを選ぶ。optimal_targets と uniform_policy が同率均等を担う。solve は物理lawを同じinfosetに集約し同じ方針を適用する。真狩人や護衛先をキーに足す必要はない。

新root入口は root_scope/root_screen_eligible/root_replay_eligible が昼夜randomに限定。guard_model.scope_reasonは連続なしのmaxを拒否。public_guard_branch_lawとreplay_root_secretsは均等襲撃確率を直接使用しているため、制限を外すだけではmaxのjoint履歴にならない。

## 実装前に再現した未定義境界

3人生存、狼P3。公開jointlawは狩人P1が3/4、P2が1/4。護衛は自護衛なし・連続あり・均等。狼は狩人を知らず、合法襲撃先P1/P2を同じinfosetで比較する。既存評価器で村勝率はP1襲撃1/24、P2襲撃1/8。狼maxはP1のみを選ぶ。

GJの物理確率は1/8で、P2狩人がP1を護衛した履歴のみが存在する。しかし公開Model AのGJは狩人生存の互換性だけで配役を保つので、P1狩人の公開重み3/4も残る。この配役には選ばれたP1襲撃を防ぐ合法護衛がなく、秘密履歴支持はゼロ。既存 enumerate_guard_history_mixture は guard_public_history_zero_support を返す。これはoracle選択や計算予算の問題ではない。

公開重みを消せばModel Aが変わり、均等襲撃や非最適襲撃を足せば設定済みmaxが変わる。現契約にはこの配役の条件付き秘密履歴を定義する規則がない。rootの将来夜はその公開lawから再び狼infosetを作るため、汎用的なmax継続を数値化する前提が欠ける。既存の終盤maxは秘密履歴が後続選択へ不要な場合の値を扱っており、完全joint履歴への拡張とは区別する。

最小再現を tests/test_hidden_guard_max_support.py に固定。ゲーム実行コードは変更せず、均等への黙った代替も追加しない。

## 決定後の接続順

1. Model A正重み・設定済み方針支持ゼロの扱いを決める。決まるまではその観測枝を明示Pendingとし、配役や秘密支持を補完しない。
2. 公開wolf_policyから得たinfoset別kernelを、GJの公開世界内履歴生成と保存履歴replayへ共通に渡す。Qは配役ごと正規化、Pは実際の方針×護衛×観測の枝質量を保持。
3. root入口の昼設定／夜maxを段階解放し、将来夜も同一設定のwolf_policy/solveを使う。既存max例外・同率処理・合法候補・継続を共有。連続なしでは各hypothesisの前夜護衛を残す。
4. 複数夜GJ、公開/狼本人、履歴編集/取消、cache、旧max値を検証。予算250000work/20秒を維持し、超過はPending。rootは履歴圧縮なし・flow memoなしなので、一般複数夜maxの実測は別途必要。

現時点で一般対応は未実装。先延ばしする技術的理由は土台不足ではなく、上の具体的な未定義支持境界。特設モデルや未承認の方針補完で通さない。
## 追加調査：通常Boardからの到達性と一般処理（前節の結論を修正）

人工jointlawの不一致だけでは全実装の凍結理由にならない。非最適襲撃の補完や新しい配分が必須という読み方を撤回する。公開観測の**戦略支持フィルター**で配役候補を除外する一般処理が候補になる。実行コードには未適用。

### 手計算できる合法な4人入力

市民2・狩人1・狼1。自護衛なし、連続護衛あり、護衛均等、昼random、夜max。P1が狩人CO、他3人は潜伏。狩人CO条件はnone（COした人数による真役職強制を使わない）。これは既存ClaimPolicyの合法設定で、COの最適化は行わない。Day1にP4を処刑し、終局でない枝のDay1夜へ進む。

通常migrate_game/replayで夜の公開配役は次の5候補、各1/5になる。W/Hは狼/狩人。

| 配役 | 狼infosetのmax襲撃 | GJ尤度 |
|---|---|---|
| W1/H2 | P2・P3各1/2（H2/H3/H4を知らない共通方針） | 1/4 |
| W1/H3 | 同じP2・P3各1/2 | 1/4 |
| W1/H4（狩人死亡） | 同じP2・P3各1/2 | 0 |
| W2/H1 | P1のみ | 0 |
| W3/H1 | P1のみ | 0 |

W1ではP2/P3襲撃の村勝率が各1/18。W2ではP1=0、P3=1/6、W3ではP1=0、P2=1/6。既存情報集合評価・同率処理で確認。真狩人位置によって行動を変えていない。

GJを入力すると既存公開replayはH4死亡候補を消し、残る4候補を各1/4にする。maxで生成した全狼rosterの観測枝はW1/H2とW1/H3だけで、物理GJ質量は1/10。W2/H1・W3/H1は自護衛不能なP1襲撃なので、秘密履歴支持ゼロ。通常の初期日から非終局夜へ進む最小人数は4人（3人開始では昼処刑後に終局）。証拠task-6/wolf-max-legal-board-proof.json、回帰test_legal_four_player_board_global_support_and_past_policy。

### 現契約の根拠と両立しない二点

- `exact.condition_claims`：公開COと設定済みCO条件の互換性で除外、残る既存配役重みを再正規化。観測されたCOを生成する未定義の最適CO方針は作らない。
- `phase_updates.condition_night_corpse`：狼選択方針の尤度を掛けない。自襲撃禁止と護衛失敗の物理互換性を条件付ける。
- `guard_model.condition_guard_observation`：GJは狩人生存という支持で配役を保ち、襲撃先が不明なので襲撃事前を捏造しない。死体時は均等護衛の失敗確率を使用。連続なしは`condition_joint_guard_observation`で世界内護衛履歴を平均する。
- `root_secret_flow.observe_root_public`：外部BoardのModel A配役重みを世界ごと復元し、その世界の秘密履歴を正規化。全ての正重み配役に秘密支持が必要。
- ユーザー仕様は公開配役重み／世界内秘密混合／物理枝質量の分離を要求し、正重み・秘密支持ゼロでは一律補完せず報告するよう指定。これは支持ゼロの候補除外を永久禁止する指定ではない。

現在両立しないのは「公開観測に対して設定済み狼方針の支持を一切使わず、W2/H1・W3/H1を残す」と「同じ設定済みmaxから生成した秘密履歴だけで各公開配役を構成する」の二点。このケースでは均等襲撃履歴を補う必要はなく、公開観測に対する全rosterの戦略支持を使うかだけが未決定。

### 支持フィルターと完全Bayesの違い

観測前公開配役重みをq(r)、既存観測条件付け後をq_obs(r)、全公開jointlawと当該夜の設定済みkernelから計算した観測支持をL(r)とする。

- 支持フィルター：`q_new(r) ∝ q_obs(r) * 1[L(r)>0]`。正の尤度の大小は配役に掛けない。各残存世界の秘密履歴は、その世界内でだけ生成方針×護衛×観測を正規化する。
- 完全Bayes：joint観測枝の質量全体を正規化する。例えば同じ生成元を使うなら`q_new(r) ∝ q(r)*L(r)`。既存q_obsにL全体をもう一度掛けると護衛観測の二重計上になりうる。実枝Pはこの物理生成・観測質量で進むが、公開Model AのQと同一視しない。

この4人例では正支持の2候補のLがともに1/4なので、どちらも各1/2になる。数値が一致することは一般モデルの同一性を意味しない。Model Aの現設計に最も近い拡張は支持フィルターで、完全Bayesへの置換ではない。

`enumerate_guard_history_mixture.role_support/zero_support_roles`は全roster kernelから支持を返せる。正支持のroleだけを既存`replace_worlds`で再正規化し、`observe_root_public`で世界内lawを再投影する案が既存部品で通ることをテストした。いまのAPIは固定全重みを受け取り、ゼロがあればPendingにするため、支持除外はまだ製品処理に入っていない。連続なしの生成は`guard_choices(...guards=h.guards)`を用いる共通flowで行う必要があり、旧mixtureの連続あり専用列挙をそのまま適用しない。

支持の生成元は公開所有の完全jointlawで、全ての狼initialroster、自身の過去襲撃infoset、各方針の正確な同率分布を周辺化する。ownerで絞ったlawや、今夜固定護衛・固定襲撃の本人介入を公開支持に渡さない。公共のGJから狼P1を推論することと、本人だけが知る狼P1を公開へ漏らすことは異なる。

### 過去入力と今夜以降の予測

`seer_manual._replay`は各history[i].policyを読んで当時のCO/観測を再生し、最後に現在policyを読む。ただし現在の夜観測は狼選択尤度を無視するため、過去maxでも上の4候補が残る。`root_secret_flow.replay_root_secrets`は各step.policyによる秘密生成を意図するが、現在はrandom限定で襲撃確率が直接均等。`public_history_key`には各Boardのpolicyも含まれる。

同じGJで当時night=randomなら4候補すべてに支持があり、GJ物理質量は1/5。現在night=maxへ変更しても、過去randomをmaxに置き換えてW1だけへ絞ってはいけない。この区別を通常保存gameとテストで確認。今夜以降の予測は現在の設定戦略、過去の公開支持は各当時Boardの設定戦略を使う。過去盤面を外生what-ifとして入力した場合、記録方針を実行法則として扱うかは仕様で明確にする必要がある。

**必要な判断は一つ：各保存Boardの方針をその夜の生成法則とみなし、全公開jointlawで観測支持ゼロの配役だけを公開候補から除外してよいか。** 推奨は可とし、残るModel A重みを再正規化する一般支持フィルター。非最適襲撃補完は不要。今後も全公開支持がゼロなら明示Pendingとし、worldやhistoryを捏造しない。

## 承認済み支持フィルターの実装チェックポイント

ユーザーは、各Boardの保存戦略を当時の生成法則とし、公開jointlawの観測支持ゼロ配役だけを除外、残存Model A重みを再正規化する方式を承認した。以前の仕様判断待ちは解除済み。

`public_observation_support.condition_generated_support`を実装し、共通`public_guard_branch_law`へ接続。公開世界内履歴を生成してから支持ゼロ候補を除外し、配役ごとに元のQ重みへ再投影する。正支持の尤度大小はQへ掛けない。役職別の特例はない。完全public wolf infoset kernelを明示入力でき、全infosetが揃わない入力を拒否する。maxでkernel未確定ならguard_max_public_kernel_unresolved、全公開支持ゼロならpublic_generated_observation_zero_support。maxを均等へ代替しない。

合法4人Boardのmax kernelを渡した共通関数が、狼P1の2候補各1/2を返すことを回帰確認。公開Q=3/4・1/4、GJ尤度=1/8・3/8の別テストでは、Qは3/4・1/4のまま、物理Bayes質量なら1/2・1/2になる差を確認した。既存random経路は同じ共有関数を利用する。

### 残る実装阻害：候補評価と今夜のkernelの循環参照

承認済み公開支持の意味は変えない。現在のwolf_policyは、各候補をactで継続評価してから分布を確定する。そのactの非終局GJで、公開履歴生成に今夜の全wolf_policy分布が必要になる。単純に公開履歴生成からwolf_policyを呼ぶと、同じBoard・同じ公開jointlaw・同じwolf情報を再び評価する。

合法4人例の隔離診断で、終局枝の不要な処理を除外した後も、Day1夜・P2候補・GJの同一sourceを再参照した。2回目で意図的に停止した証拠はtask-6/wolf-max-policy-dependency-proof.json。これは製品経路へ追加しておらず、無限再帰や暫定均等分布は入れていない。

解決には、当該夜の候補比較における介入と、選択後の全infoset方針による公開観測生成を計算上分離し、最終選択分布とその支持・継続評価の整合性を検証する計算器が必要。現在の行ごとのactをそのまま循環させる接続では足りない。複数の自己整合分布が出た場合の任意選択や未検証の暫定方針は追加しない。root maxの適用ゲートはまだ解除していないため、**狼max拡張は未完成**。過去方針への遡及適用、狩人最大化、CO最適化は行っていない。
