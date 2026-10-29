# 実ユーザー7人情報・均等準備だけのcheckpoint

対象は市民3・霊1・占1・狼2、P1/P2占COがともにDay1 P4白、P3霊CO、全員生存。保存された `actual-seven-max-results.json.game` がこの公開情報に一致する。別のM0/白P3の古い7人入力とは区別した。

`cut_out_user_seven_uniform_preparation` に局所的な準備専用入口を作成。比較入力は保存gameのpolicy.day/night/fake_reportsだけを明示的にrandomへ変更し、それ以外の設定・公開log・同時batchは全て保持する。3項目以外の差を持つ入力や元のmax入力をprepareへ渡すとunsupported。元データや通常UIは変更しない。

これは本来の初期max対応ではない。勝率・完全Forecast・速度測定は実行せず、forecast入口も明示unsupported。7人用の発行済みsource保証もまだ作っていない。

## 小さな検証で分かったこと

| 項目 | 確認結果 |
|---|---|
| 初期prior | 既存BoardData/SavedOriginの準備のみで6配役・6秘密状態 |
| 公開重み | P1/P2は真占各1/2・狼各1/2、P3真霊1、P4市民1 |
| 同時報告群 | 既存ConstructiveCutOutGroupsで `{1,2} / {3} / {4} / {5,6,7}` |
| 狼本人情報 | 6情報集合、初期rosterは各2bit。狼1のモデルへ置き換えない |
| 共通保存夜 | 均等RootSecret replayは狼2の合法手・物理混合を既に扱える |
| 旧照合/全探索 | canonical/CandidateRules/solve/act値評価の呼出し全て0 |

COと同時報告の分割は既存の構造規則を使う。reporter1/2は同じtarget/color/取得日を持つ一つのsimultaneous batchとして保持し、行ごとの点固定で最初から分離しない。完全jointに対する交換検査をテストだけで実施した。

## 合成の第一夜prefix（実ユーザー履歴ではない）

実入力はまだ全員生存で、第一夜後の観測は与えられていない。到達可能性の部分検証用に、処刑P7→襲撃P6→Day2 P1/P2白P7・P3霊白P7という別の合成saved timelineを作った。初期情報とrules/均等方針を継承し、既存replayだけでsourceを準備した。合成側は新しい保存timelineとしてowner/input revisionを0で揃え、元ユーザーsnapshotのrevisionを流用していない。実ユーザーの履歴として保存・公開していない。

7 replay境界でQ/Pの群継承を確認。翌朝の報告を適用する前は「P7が初期狼」の公開Qが1/2、物理Pが4/9となる。処刑P7が狼だった世界では生存狼1・合法襲撃先5個、狼でなかった世界では生存狼2・合法襲撃先4個となり、均等でも観測方針尤度が変わるためである。Q/Pを同一視できない。

初期simultaneous batchの保証を使う局所observerにより、P1/P2の交換可能性は死亡・第一夜の混合後まで残る。次のDay2報告はこの合成入力ではlegacy観測で、既存snapshot observerは新reporterを一人ずつ点固定する。最終sourceは2配役・2秘密状態で、保守的な群は全singletonになる。この分離は誤った結果ではなく過剰制限であり、次の同時batchを再び共有したいなら、そのbatch情報を持った差分保証が必要。

初期の既存priorはtracked=(1,2)、保存replayの完全履歴sourceはtracked=None。ロスター・取得・攻撃履歴を含むそれぞれの実際のメタデータを保持した。初期report適用時のhypotheses一致は小さな整合性検査であり、メタデータを強制的に同一化したり、そこから汎用source保証を発行したりはしていない。最終合成sourceは同じ保存入力から作ったSavedOriginのQ/P/physical/past全体と一致する。

## 欠落条件と分類

1. **配役descriptor/入力adapter（保守的なprototype制限）**: InitialModelASpecにwolvesがなくsource_gameもwolves=1固定。7人minimal入口はM0・initial none・既知狼1・小支持専用。実7人が6状態だからといってW1のbaseline・配役重み・nominal countをそのまま使わない。局所PreparedSevenはGameDataのwolves=2を保持するが、評価engineが受ける発行済み7/W2 adapterではない。次は実cast7/W2/M1/S1/H0を明示するadapterと初期receiptが必要。
2. **二人狼の物理混合（基礎kernelは既存対応、専用helperは制限あり）**: RootSecret均等replayは今回通った。一方CutOutDayNight/ObservedActionのW1仮定やCandidateRulesのroster1bit前提を流用できない。特に生存狼数混合と初期roster2bitを維持する。均等経路ではmax候補証明を呼ばない。
3. **同時reportの差分保証（過剰制限）**: 初期batchの構造は既に表せる。一般snapshot observerの個別点固定は安全だが交換可能性を失う。後の報告も共有するには、明示されたbatch provenanceと初期/後続それぞれのstabilizer証明を継承する必要がある。
4. **第一夜後source issuer（未実装の型付き橋渡し）**: 現SourceWitnessの発行範囲は厳密にSixInputRegistry/6人狼1。7人へ流用しない。origin/入力/revision/owner/完全Q/P/physical/pastを束縛する7人用scope/parserを作り、保存観測の完了receiptから発行する必要がある。Binding機構の考え方は再利用可能だが人数ガードだけを外す変更ではない。
5. **実際の第一夜後入力（未提示情報）**: 上記は合成検証。ユーザーの実第一夜後sourceとして保証するためには、その保存観測・報告・所有revisionが必要。
6. **本来の初期max（未対応として保持）**: uniform準備成功から最適なCO/報告/複数max方針を作らない。7/W2の新機構での全継続評価・戦略証明はこのcheckpointの外。

## 資源と次の境界

部分probeは0.141秒、PeakWorkingSet36,151,296 bytes。追加の軽量2回帰は0.828秒で成功。初期とprefixのQ/P交換14件を確認。solve/actを呼ぶと即失敗するmock、旧canonical/CandidateRulesを呼ぶと即失敗するmockの下で全準備が完了した。worker30秒・prefix replay10秒・RSS1.5GBの上限内。

次は7/W2の明示descriptorとbatch-awareなsource保証の設計・限定移植までが候補。全探索・完全Table比較・速度測定は次の許可枠を待つ。旧照合fallback、通常UI接続、サーバー変更、push/deployは追加していない。

結果/source SHA256: `benchmarks/player_match_groups/cut-out-user-seven-preparation-results.json`。軽量log: `.artifacts/user-seven-preparation-light.log`。
