# 途中registry → source群保証の橋渡し案（未実装）

反復計測後に検討する安全境界。今回は設計のみで、SixInputRegistryのroutingやreplay処理は変更しない。

## 最初に通す範囲

既存6人・均等・W1/S1/H0・最小2初期形状から、保存された初日処刑と第一夜の死亡をreplayした現在sourceを最初の対象とする。初期COは固定、途中CO・履歴COの変更/撤回、max、狩人/GJ、7人、未定義の秘密支持はunsupported。各過去stepのpolicy/rulesも均等scopeに入ることを確認し、現在の設定だけで過去を上書きしない。

現在のSimpleNamespace/start().groupsを型だけ許可して取り込む変更は行わない。保存データ不足ではなく、現sourceに対応した因果的な保証が発行されていない点を解決する。

## 保証の発行と結合

1. 保存された初期入力から既存ModelA初期群を発行し、実際の初期CO・初期報告に結びつける。現在Boardの周辺配役から初期群や秘密履歴を作り直さない。
2. 既存replayの完了境界に観測専用フックを置き、親保証と「この完了済み演算はその群に関して等変」という限定された演算種別から子保証を作る。死亡/公開報告の新しい端点だけを固定し、均等取得では公開群を保つ。法則の行比較・置換探索で群を発見しない。
3. `replay_root_secrets`の保存夜は特に、設定済み狼本人方針でPを重み付けし、物理枝を混合し、その後にQを復元する既存の境界を使う。`step_root_action`の途中の一つの狼枝やQだけから現在source保証を発行しない。保存夜を新しいActionEvidenceの行動介入で置き換えない。
4. `observe_root_snapshot`/`observe_root_public`が既存の観測条件を適用して完了したsourceへ結びつける。Qの公開配役重み、世界内秘密混合、Pの観測方針尤度を保持する。手入力報告の頻度を偽報告選択尤度として追加しない。
5. 最終保証はorigin、BoardDataの入力digest・revision・board owner、全履歴step設定、公開Board/Q、physical Board/P、pastを含むsourceへ束縛する。SavedOrigin(project_public=False)の現在sourceと完全一致することを結合時に一度確認する。この検査は同一sourceの照合であり、canonicalや同値lawの探索ではない。
6. 発行済み保証だけを受ける明示factoryでInheritedGroupRegistryへ渡す。公開群はQと観測由来Pの両方を保つ構造保証を必要とし、本人条件付けはそこから別の評価群を作る。本人role/results/行動履歴を公開方針の入力へ混入させない。future生成子は既存の取得・死亡・公開報告フックを継続使用する。

## cache・編集・取消

cacheはorigin identity、入力内容digestとrevision、rules/全step strategy、観測recipe prefix、完全sourceの整合性で束縛する。revisionだけ、現在のalive/claimsだけ、public Qだけ、周辺配役だけでは再利用しない。

編集・取消・再入力はimmutableな新SavedOrigin/sourceから保証を再発行する。古いsnapshotはその入力として読めるまま保持するが、古いactor/frameを新しい現在sourceへ流用しない。取消を戻して数値が一致しても、新bindingの発行を経ずに以前のobjectを現在sourceとみなさない。

未知の演算、scope外CO、片方のcarrierだけの一致、消えた秘密支持、群保証欠落はPending/unsupported。旧root+累積固定点、旧canonical、任意の均等補完へ暗黙で戻らない。現行の明示旧参照は比較用として分離する。

## 実装前後の有限gate

- 現在sourceのQ/P/physical/past、公開・本人Table/相関、枝massを現行SavedOrigin/旧厳密参照と比較。PとQが異なる保存夜を必ず含める。
- 1枝のlazy復元はliteral labelのまま。Table生成で全終端木を要求しない。cold replayとcache再計算で一致し、取得roster・両夜攻撃・死亡記録を保持する。
- 報告編集・取消・再入力、古いactorのstale判定、sourceを片側だけ差し替えた拒否を検証。CO変更/撤回は第一段階では明示unsupportedを確認し、将来対応時に既存のowner/時刻意味論を再検証する。
- 新経路と保存replayの全子でcanonical/CandidateRules/子のroot群再構築0を監視する。信頼できる完全source結合に失敗した場合は保証を発行しない。
- 各worker60秒/RSS1.5GB・全体有限予算を維持し、正しさを通してから別の速度測定へ進む。

反復計測では、新増分群方式は旧root群方式より約7〜8%遅かった。橋渡しの正当性と高速化を分ける。完全sourceの繰返し索引・重複する完了済みイベントの群維持は今後の計測候補だが、どの内部処理が支配的かは今回の大括りタイマーだけでは断定しない。hashを省いて不完全なキーへ変える変更や、P/Qの同一視でコストを削る変更は採用しない。
