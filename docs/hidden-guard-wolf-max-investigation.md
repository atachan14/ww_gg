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

## 4人の非選択候補評価：訂正と共通修正

追加検証で、4人例の支持外WolfInformationを作る操作が、候補利得の評価に本当に必要なのかを確認した。GJ後は3人で、昼randomの処刑はどの実世界でも終局。したがって新しい狼判断やそのoff-path信念は不要で、物理chanceの1/2（P3を護衛）×1/3（次の処刑で狼を引く）=1/6を返せる。この例だけで一般候補評価が数学的に不能とした読み方を訂正する。

実際の共通actは、観測のない朝でもobserver_report_weightsでpublicとprivateの報告尤度を求め、information_set_report_likelihood_incompleteで止まっていた。InformationSetActionPolicy.morning_valueで、朝枝が確率1・Board/joint/pastとも不変ならprivate physical lawをそのまま次へ渡す共通修正を加えた。新しい観測がないのに公開支持へprivateを再交差させない。役職・人数の特例ではなく、identity chance transitionの扱いである。実際に報告が生成される枝の尤度処理は変更しない。

選択済みpublic kernelを固定した診断と回帰で候補P3の村利得1/6、将来wolf_policy呼出0回を確認。公共GJの候補は狼P1の2配役各1/2のまま。私的にW2がP3を選んだ事実はpublic kernelへ渡していない。task-6/wolf-max-counterfactual-support-proof.jsonに追記。

公共GJ自体は選択済み方針で1/10の正の確率があり、公共のoff-path観測ではない。支持外なのは「W2であり、自分がP3を襲撃した」という狼自身の情報集合。この情報は選択済みmaxでは起こらないが、候補介入として物理的には合法。選択前のactor lawから候補遷移を作ることと、選択後のpublic支持を同一視しない。

未解決の一般範囲は、その後に支持外actor情報集合から新たな最大化判断が必要な場合、または公共観測そのものが全kernelで支持ゼロで、公共最大化主体の判断が必要な場合。actor_information.WolfInformation.condition_publicは前者を拒否し、condition_generated_supportは後者を拒否する。4人昼randomの例はどちらの判断も要求しないため、新信念の仕様選択なしで解けた。より大きな局面を同じ例だけで一括保留にせず、この依存が本当に消費される箇所を調べる。

共通エンジンで今夜の完全kernelを、選択済みpublic観測生成に入力する構造は必要。単純な再帰接続には選択分布→公開支持/世界内履歴→候補継続利得→選択分布という依存があるが、利得が公開支持に依存しない終局までの固定方針chance枝では切断できる。候補評価のために現在kernelを差し替える案は採用していない。未定義のoff-path信念をuniform等で補う修正も入れていない。

## 6人開始の後続max必要例：限定した実装チェックポイント

通常6人（市民4・狩人1・狼1）、P1狩人CO、狩人CO条件none、Day1にP6を処刑、昼random・夜max・護衛uniform。夜は5人生存で、GJ後にも昼→夜が残る。WolfInformation(P2)は公開COからH1と全配役を知る。誰かの秘密を追加していない。

fixed_actor_continuation.pyの依存切断部品で、本人情報集合を完全public入力から作り、未知の護衛選択を積分した後に共通optimal_targets/uniform_policyで選ぶ。role worldごとのoracle maxにはしない。後続actor maxは全配役が本人の既知情報で確定した時だけこの部品で評価し、それ以外は通常public evaluatorへの依存を返す。viewerで絞った入力は拒否。

P2のP1襲撃は1/4。P3/P4/P5襲撃は連続あり3/10、連続なし43/144。この評価では後続optimal_targets呼出が実際にある。未知配役のWolfInformation(P1)では後続の未知役職判断が必要になる枝がありNone（未解決依存）を返す。これは新しいbeliefを入れた数値でも、一般実装不能の証明でもない。

追加3テスト成功（0.185秒）：4人未知配役の固定終局まで、6人既知actorの後続max・両連続ルール、viewer法則と公共max判断の不使用。新部品は製品root経路へ未接続で、rootmax適用ゲートは未解除。次はpublic入力の全infoset kernel、選択後生成、実際の公共支持、owner継続を同じ局面で照合して接続する。未定義のoff-path補完、policy事後差替え、uniform fallbackは追加していない。


## 最小未知配役の製品root接続

4人開始・昼random・狩人uniform・夜maxを製品経路へ接続。RootSecretEngineが完全public sourceから全WolfInformationの候補利得をfixed_actor_valueで評価し、確定できた場合だけoptimal_targets/uniform_policyで完全kernelを返す。公開取得前sourceを取得後の夜flowへ明示して二重取得を防ぎ、private viewerをkernel生成へ渡さない。候補が後続未知判断に依存した場合はroot_guard_max_unknown_continuationで止める。

P1狩人CO・CO条件none・P4処刑の等重み例では、狼P1はH2/H3/死亡H4を知らず、P2/P3の利得各1/18・選択各1/2。狼P2/P3は公開COからH1を知りP1襲撃のみ。公開全体の夜勝率は1/30。GJ後の公開候補はW1/H2とW1/H3各1/2で、現API本人Tableと公開replayに同じ選択済みkernelが接続された。両連続ルールで確認。

実際に入力された過去max夜はその時のkernelでphysical history massを生成し、公開はゼロrole除去＋既存Q再正規化。過去random・現在maxの夜はrandom kernelのまま4候補を保持する。既存daymax経路を上書きせず、新rootではdayrandomの範囲。初期5/6人の未知配役で候補値が未確定な場合はPendingを保ち、一般対応完了としない。

通常routeでも開始→P4処刑→未知狼P1本人表示→GJ入力→再入場→戻るを検証。NoRepeat入力の新root対応を許可し、候補利得が未確定な盤面の進行は拒否して保存Gameを保持する。旧daymax/defaultmaxを均等へ置換しない。全対応までの残件は未知配役の後続判断を持つ同一公開kernelの解決。

最小製品経路の最終検証：全554テスト成功（187.357秒）。既存独立Edgeを再利用し、通常設定4人・昼random/夜maxで連続なし/ありの両方を実操作確認。初日7/24、P4処刑後の夜1/18。狼P1本人TableでP2/P3の最終村利得各1/18・狼17/18、H2/H3/死亡H4各1/3を実表示。戻る後の7/24と夜max保持も確認。証拠task-6/root-max-no-repeat-owner.json、root-max-repeat-owner.jsonおよびPNG。専用18801は所有元確認後にPID30880へ反映、HTTP200。一般未知6人の後続判断はPendingのままで①全体完了とはしない。公開は①②の完了後のみ、現在未実施。


## 固定公開方針と物理的な続行観測の確定回帰

6人・市民4狩人1狼1、P1狩人CO／他潜伏、hunter ClaimPolicy none、D1にP6処刑、昼random・夜max・狩人uniform。連続護衛あり／なしの両設定で、保持した完全公開kernel（W1はP2〜P5各1/4、W2〜W5はP1のみ）を使う。このkernel全体が最適だという主張ではなく、不成立試案の支持を再現するために明示した入力である。

GJの公開支持はW1/H2〜H5各1/4。一方、PUBLIC CO＋自分の狼役からH1を知るW2が候補P3を実行すると、H1がP3を護衛する物理GJ枝の確率は1/4。本人履歴はWolfAttack(1,3)とGuardIntent(1,1,3)を保持する。この後P1を処刑すると公開は村勝利の枝のみ、実配役はH1死亡・W2生存で続行。実際の共通actから修正前のNoneType.worlds例外を再現した。保存された元プローブの最初の失敗配役を特定したという意味ではない。

共通require_public_observationで真の終局／続行を公開観測として照合し、続行枝が公開支持ゼロならpublic_continuation_zero_supportのPendingを返す。公開の勝利予測を物理利得へ転用しない。別の公開終局枝、候補ごとの公開kernel差替え、物理配役からのbelief生成は使わない。狩人非GJ枝も同じ判定を使う。

対照としてP2を処刑すれば実配役では村勝利であり、公開側が続行を予測していても物理利得は1。さらにW2の候補P3全体は既存fixed_actor_valueから連続あり3/10、連続なし43/144を得られる。本人は当初から全配役を知るため、支持外の公開継続beliefは不要。公的な続行支持を確認する共通経路と、追加beliefに依存しない本人継続の依存切断を区別する。

追加2回帰＋既存9重点回帰が成功。一般未知6人の完全max kernel解決はまだ未完了。全支持ゼロ時に任意beliefを足す契約は導入していない。②を先行せず、①・②完了後の公開ゲートを維持する。

今回の対象そのものの全回帰は556テスト・188.639秒で成功。重点11テストは4.386秒。新しい完全kernel試案の再実行はしていない。


## 未知6人継続：全候補の共通評価証明

②を完了したa43c4c1の上で、C4/H1uniform/W1・昼random・夜max・公開能力報告なしの未知6人を接続。本人lawだけで進めた未知配役候補値は内部提案に限定し、完全PUBLIC sourceから全wolf infosetのkernelを組む。固定した完全kernel下の既存共通action/evaluation flowで未知役職の全候補値をFraction比較し、すべて一致した場合だけ採用する。不一致はroot_actor_continuation_belief_divergence、未検証はPending、失敗したkernelはcacheから除去する。共通値を確定する前に均等fallbackや仮の値を公開しない。

証明の開始はPUBLIC由来のWolfInformation（役職roster＋自身の襲撃履歴）であり、途中の物理分岐は自身の行動と公開された死亡/GJだけで分割する。それらによって配役を完全に知った継続は、公開側がその非選択襲撃履歴を持たなくても既存の既知本人継続で評価する。真の配役worldを先に一つ選んでmaxせず、未知の他人の護衛履歴は混合したまま。guardian/seer viewerの秘密をこの入口に入れない。

fixed_actor_valueの既存呼出しは既知役職cutのまま。未知役職のactor-only仮計算は明示opt-inで、他の選択が固定されたC/W/Hの範囲だけ。未知役職の物理measureとactor beliefの役職重みが異なる場合はその仮計算を使わない。公開Q、world内の秘密履歴混合、物理Pを置き換えない。真に必要な公共支持がゼロなら従来どおりPendingであり、任意beliefは補わない。

②の完全joint正準keyを、純粋な候補提案と検証済みscalarに再利用。元の候補ID・同率多重度を保持し、physical/joint ledgerを圧縮しない。各保存夜のkernel検証と各物理actionは同じRules/その夜のStrategyのengineを共有し、過去randomを現在maxへ変更しない。

6人P1狩人CO・hunter ClaimPolicy none・D1P6処刑後：両護衛ルールの公開村1199/4320、P1狼本人の合法P2〜P5各719/2400。PUBLICの行P1は1/4、他行はrepeat1151/3840、no-repeat383/1280。ActorP1の選択は4候補各1/4。過去maxGJ→D2P3処刑後は4世界で村23/72。過去randomGJ→同じ死亡では7世界を保持し、現在maxの村はrepeat79/252、no-repeat13/42。本人が過去P2を襲撃してGJならH2を除外し、死亡H3と生存H4/H5の支持を残す。

回帰は仮候補値を故意に変えた場合の拒否/cache除去、Pをactor Qに使う試みの拒否、両護衛・max/random保存歴・複数夜GJ/死亡・戻り保存を含む。最終全565テスト224.288秒成功。ブラウザー6人確認と18801のこの修正への再起動は次の検証であり、現時点では未実施。public reportingを伴う新max、guardian自身max、同時複数maxの一般化は今回追加しない。

### Browser checkpoint (2026-10-14 20:32 UTC)

Dedicated localhost:18801 was restarted after verifying its owner, using code d89cf200cdb330f1c2dd6be0deb286d6f6d8427a (PID 23428). Ordinary browser controls exercised C4/H1/W1, equal public role weights, hunter CO policy disabled, P1 hunter CO, day random/night max, and D1 execution of P6.

For both repeat-guard rules the public village value was exactly 1199/4320. Wolf P1's legal targets P2..P5 each showed 719/2400 (wolf 1681/2400); self and dead P6 remained blank. Public restoration recovered P1=1/4 and P2..P5=1151/3840 with repeat guards, 383/1280 without. Repeat-guard public reload retained every exact candidate fraction. Back returned to Day1. No-repeat reload and back/re-execution reproduced the entire public fraction snapshot exactly, retaining the configured max policy. Evidence: task-6/actor-browser-*.json, including actor-browser-consistency.json (reloadEqual=true, replayEqual=true).

All 565 backend tests passed before this documentation-only checkpoint (224.288 seconds; actor-common-proof-full-final.log). The earlier seven-player symmetry on/off exact comparison and browser checkpoint remain complete. General unverified max closures, report policies and mutual max remain explicitly Pending as documented in HELP; this checkpoint does not expand that scope. No push or deployment was performed. Dashboard task-c857928fd4324a51 update remains held following automatic approval rejection for mismatch with the originally authorized task ID; parent is obtaining explicit authorization.


### All-latent six-player checkpoint (2026-10-14)

The ordinary C4/H1/W1 all-latent board now completes at the existing 250000-work / 20-second budget, without changing rules or policies. Day random, guard uniform, wolf night max: D1 is exactly 1199/2880, all execution rows equal, dawn village mass 1/6; after P6 execution N1 is 719/2400, all five attack rows equal, dawn winner masses zero. Both repeat-guard settings agree. Cold timings were 8.354/6.511 seconds (repeat, D1/N1) and 7.058/4.988 (no-repeat).

The root engine had disabled flow memoization even after the complete-ledger symmetry implementation became available. This expanded the common proof repeatedly (996 action / 398 value expansions at a profiling deadline). Enable full-input action/scalar memoization for wolf max only, retaining every joint history. Keep proof actor identity separate from ordinary evaluation; failed renaming falls back to the entire identity input, never a reduced descriptor. Candidate physical backups now share completed scalar values within the same engine, keyed by Rules, Strategy, proposal/strict mode, full Board/law and forced action. No None/Pending value is cached. The same all-latent N1 profiling completed with 137 action / 70 value expansions; unprofiled evaluation completed around 6.4 seconds. Public Q, actor belief and physical P remain distinct. No new CO/report policy or max replacement.

Focused validation: 25 prior actor/history tests passed (26.985s); 21 actor/root/full-renaming tests including three new regressions passed (51.337s). Full suite and live UI follow this small code checkpoint.

Remaining scope: ordinary all-latent six-player day-random/guard-uniform/night-max is addressed. Root day-max/night-max is still explicitly gated (not silently random); unknown-role wolf continuation with seer/medium/report decisions is not generally closed or certified. These are remaining general-entry integration work, separate from inventing optimal CO/report rules, hunter max, or a new mutual-max equilibrium, which remain deferred. More players/long GJ histories may still reach the existing budget; mismatched or zero-support histories stay explicit Pending. General task ① is not declared complete by this checkpoint; ② remains complete. No publication.

Full validation after 98dc121: all 568 tests passed in 229.426 seconds (task-6/latent-six-full.log). Dedicated 18801 was owner-checked and restarted with 98dc121, actual listener PID492; HELP HTTP200 contains the new scope statement. Ordinary browser controls confirmed both repeat-rule settings for all-latent D1=1199/2880 and N1=719/2400, wolf P1 owner legal rows=719/2400, self/dead rows blank. Back restored D1. No-repeat saved/reloaded public rows matched the entire exact Fraction snapshot (latent-six-browser-consistency.json, exactSnapshotEqual=true). Evidence: task-6/latent-six-browser-*.json. This closes the all-latent six-player performance checkpoint; general task ① remains in progress, as distinguished above. No push/deploy.

### Day-max/night-max minimal closure probe (2026-10-14)

Read-only common-engine experiment: C2/H1/W1, P1 hunter CO with hunter claim policy none, P4 executed, N1 alive P1/P2/P3, repeat guard enabled, guard uniform; change only day=random to day=max. No product gates were removed and no policy/observation law was replaced. For the three wolf infosets there are two legal targets each, hence 3^3=27 possible max/tie-uniform kernels. For each candidate, the existing common action evaluator used that SAME complete public kernel for all candidate attacks. Exactly one fully evaluable candidate was self-consistent: all three infosets choose their two legal targets at 1/2 each. Its W1 candidate village values are 1/6 each; W2 and W3 candidates are all zero. Six candidate kernels raised public_generated_observation_zero_support; remaining evaluable kernels failed the best-response equality. Probe and raw evidence live in task-6/day-max-four-kernel-probe.py/.json.

This demonstrates a feasible common-flow certificate for the minimal day-max combination, but does not prove a general unique solution. The dependency is wolf kernel -> generated public GJ support -> public day-max choices -> wolf candidate scores -> wolf kernel. Using a private-role day-max backup would leak wolf knowledge into the village policy; simply removing the root gate would not solve this dependency. A general continuation solver must certify an entire public kernel and handle cycles/undefined candidate observations explicitly, without inventing off-path beliefs or choosing an arbitrary equilibrium. No code expansion or declaration of day-max support was made by this diagnostic checkpoint. Occupation/report continuations remain next, after this closure is resolved.
