# 6人最小・均等二夜への増分群移植checkpoint

既存 `3240ad1` の6人二夜ケースに、4/5人で確認した親→子の群継承を局所移植した。新入口は `benchmarks.player_match_groups.cut_out_six_inherited.evaluate`。通常UI、既定の6人評価、途中Board registry、7人、maxのroutingは変更していない。速度計測前の正しさcheckpointである。

## 接続できた範囲

既存の明示的な6人Model A初期root、W1/S1/H0、均等day/night/fake report、初期random_whiteを使用。入口は3240ad1の次の2形状だけを受ける。

- M0、P1占いCO・初期白P3、他は潜伏。公開・本人占い・本人狼を検証。
- M1、P1占いCO・初期白P4、P2/P3霊能CO、他は潜伏。既存の公開報告混合を検証。

共通registryの初期人数ガードを明示的six opt-inにし、engineのregistry生成口だけを差し替えた。死亡・均等取得・公開報告・本人群の分割ロジック自体は4/5人版と共通。必要なroster、初期joint、二夜の取得/攻撃履歴、公開/本人/physical carrierは既存SavedOriginとレシピに全て含まれていた。新しい履歴の生成意味論や方針は追加していない。

4/5人版の初期人数ガードは、この6人初期rootに対しては情報欠落ではなく保守的なscope制限だった。6人の各共通遷移にも同じ局所証明を適用でき、初期群へ全履歴の固定点を適用し直す経路を使わず子へ渡せた。

## 有限検証

公開・本人占い・本人狼・霊能COの4数値ケースと境界1ケース、関連9回帰テストが24.906秒で成功。各worker60秒、全体270秒、PeakWorkingSet1.5GBを維持。数値ケース最大4.110秒、PeakWorkingSet最大82,169,856 bytes。これは参照評価・全終端読戻し・検証を含む実行資源記録で、製品性能の測定ではない。

| ケース | 村勝率 | 継承子 | 最大深さ | scalar/旧群一致 |
|---|---:|---:|---:|---:|
| 公開 | 3/8 | 507 | 7 | 438 |
| 本人占い | 3/8 | 507 | 7 | 438 |
| 本人狼 | 3/8 | 198 | 7 | 133 |
| 霊能CO | 3/8 | 1,509 | 8 | 1,103 |

合計2,721継承子、2,112scalar/旧群比較、公開jointの交換不変性889件、本人joint/physicalの交換不変性528件。Table/Forecastは「旧root+累積履歴で群を作る経路」と「旧全ラベル厳密参照」の両方に一致。終端の公開/本人joint、physical、past、observer、枝質量は全ラベル参照と一致し、二夜目のroster3個・両夜のWolfAttack・死亡占い師の取得・死体占い対象の証拠も保持した。

新経路の評価と終端再構成を、呼ぶと失敗するmockで監視。再帰canonical、CandidateRules、初期群再構築、子での初期prior再構築は全て0回。二夜目の1枝はkernel reuseを無効にした真のcold再読込でも一致し、群の旧照合へ戻らない。cold replayが保存INITIAL priorを再構築することと、子を新しい初期priorとして扱うことは区別している。

旧6人経路もcanonicalによる対称性探索は既に無効だった。今回の改善はroot+累積履歴による群再構成を、親群の増分分割へ置き換えた点。3240ad1の既存代表評価削減を新しい速度改善として二重計上しない。速度・end-to-end優劣は今回測定していない。

## 対象外の原因

- 途中Board用SixInputRegistry: 保存データは存在する。現在のSimpleNamespaceによる群と過去CO編集・取消の全履歴を、現在sourceへ結びついた発行済み増分群保証へ接続する橋渡しが未実装。データ不足を一律補完する問題ではなく、今回はその保証を持たない入口として明示unsupported。
- 上記2形状以外の均等6人初期入力: 最小比較範囲を守る保守的なgate。履歴が欠落しているという意味ではない。新たな対象を通す際は局所の保証・資源・結果一致を確認する必要がある。
- 6人max、7人、狩人、占い師複数: 既存の均等adapter/方針証明の外。人数ガードだけを外して対応済みにはしない。
- 発行されていない子source、失われた群保証: Pending/unsupported。旧root群処理や旧照合への暗黙fallbackはない。

全joint生成・完全sourceのcacheキー・候補/物理枝の厳密評価・全ラベル表示木の任意出力は引き続き別のコストを持つ。通常UI統合や任意の途中Board編集へ適用したという主張はしていない。6人の既定経路は比較参照としてそのまま保持し、採用変更は次の工程とする。

結果: `benchmarks/player_match_groups/cut-out-six-inherited-results.json`。回帰log: `.artifacts/six-inherited-focused-final.log`。worker60秒/RSS1.5GBを超えるheavy aggregate、速度計測、サーバー操作、push/deployは行っていない。
