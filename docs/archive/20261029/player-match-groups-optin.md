# Player view／被申告indexと一致グループ：明示切替の限定接続

基準63c4af9、数理基準03e4e31。c872d19の圧縮継続・厳密置換・監査に必要なlogicだけを `werewolf/match_groups.py` へ移しました。e203aacの単一状態再利用、browser試作、生成前orbit試作は取り込んでいません。information_weights.pyは公開03と一致します。

## 入口と既定

`model_a_public.public_forecast(..., match_groups=True, match_view=public_player_view, match_audit=True, diagnostics=stats)` が内部の明示入口です。既定はFalseで、通常UI／API／保存設定からこの引数を渡す接続はありません。通常の呼出では従来のInformationSetForecastをそのまま使います。数値cacheを切替flagなしで共用する新しい永続経路もありません。今回、既定を有効にはしていません。

有効になるrootを以下に限定しました。

- 公開視点、初日昼、全員生存、過去行動／報告なし。
- 5人1狼／6人1狼／6人2狼。占い1・霊0・狩人0。
- CO占い1人が公開支持上で真占い確率1、残りlatent。完全な全配役支持と一様な役職共同分布。
- 初日占い取得なし、取得／護衛／襲撃履歴なし。自噛みなし。
- 設定済みday/night/fake-mediumはuniform、既存の未訪問優先uniform占いと承認済み偽報告規則。

圧縮する子の境界は生存5人以下です。max、本人view、狩人、9人、初日ランダム白や一般の公開報告付きrootなどは新経路を有効にせず、元の設定のまま旧flowへfallbackします。maxを黙って均等へ置換しません。

## view/indexの接続と証明

PublicRelationsはPlayerDataのcurrent CO／生死、co_historyとreceived_claimsを読む、軽い不変構造です。被申告の宣言者・対象・役・取得日・色・公開slot/day/phase・batch mode/orderを保持します。Name、表示用の丸め率、個々の役職率は判定入力にしません。CO表示groupとは別責務です。

rootの関係だけで作るcandidate groupは候補であって、共同分布の同値証明ではありません。実際に枝を共有するには、既存canonical_keyで子のBoard、公開joint、本人／物理joint、全役職mask・秘密履歴・確率質量、公開履歴、Rules／Strategyとphysical Boardの完全置換一致が必要です。さらに、その置換でrootの公開関係も一致することをキーへ追加します。候補groupを独立確率として掛け合わせません。rootの候補群を使ったcanonical探索自体の高速化は今回していません。

公開の秘密候補は、同じ実際の未公開結果を持つことを要求せず、共同分布全体が置換で対応するかを見ます。public evaluation内部のwolf情報／物理分布は別入力として完全に保持し、個人の秘密を公開の行動選択へ渡しません。外部の本人Tableでは新経路を無効にします。

訂正取消ではindexを現行の正本から再生成し、root relationsも作り直します。新しい対象関係や観測で一致が壊れれば別キーになります。これらをGame共通cacheへ保存しません。未来の全BoardへPlayerDataやUIログを複製せず、rootの軽い関係tupleだけを共有します。

生成・公開尤度接続・公開後の再構成は元のflowのままです。その後の同値な継続を確率質量の和で1代表にして評価します。最初の全ラベル付き報告生成はまだ圧縮しません。root Tableは各元IDの行を個別に維持し、内部の継続scalarだけを共有します。値を周辺率だけで別のプレイヤーへコピーしません。

## 完了した厳密比較

5人1狼7/15、6人1狼3/8、6人2狼1/12まで全て完了し、新旧の最終値・Table全field・役職率・各行の次朝指標が一致しました。監査モードは、全まとめ対象枝の質量・完全な公開/本人/物理署名、置換後役職率・合法手を比較し、元の各枝を独立したgroup無効engineで終端まで評価して値を照合します。

| 6人 | 行動展開（旧→新） | 取得状態（旧→新） | 時間中央値 秒 | process Peak WS中央値 MiB |
|---|---:|---:|---:|---:|
| 1狼 | 2366→1766 | 871→651 | 1.240→1.070 | 39.81→36.78 |
| 2狼 | 2456→1856 | 906→686 | 1.362→1.202 | 40.52→37.69 |

各新経路で、訪問した継続batchの合計は240ラベル枝→180代表、solve呼出987→747、value展開909→669。生成報告枝145は同じです。既存のcacheは両方で有効なので、既にcacheされた呼出の数え直しだけではありません。5人controlでは最終値は一致するものの追加削減はありません。

各設定はfresh子プロセス3回、AB/BA/AB、engine20秒/100万work、外側30秒。計時は準備済みrootからforecast完了までで、root view準備は両側で計時前、最終Table投影は計時後です。root関係生成・判定／厳密証明と計算は計時内です。監査用の独立旧engineを動かす時間とメモリは性能測定に含めません。Peak WSは起動・import・準備・出力も含むwhole childです。小標本の限定結果で、一般の高速化率保証ではありません。

## 9人の有限生成診断のみ

既知真占い1・狼2の初日取得なしrootで、3秒/10万workを上限に診断。0.073秒で28配役、公開構造候補[1]／[2..9]、完全なroot jointでも28個の入替が不変と確認。次の通常占い生成224状態、質量1、各対象P2..P9は1/8でした。

これは元の生成の診断です。224状態を減らした結果ではありません。9人のgroup solverは無効で、未来勝率探索・完了性・高速化は測っていません。

## 回帰・残件

最終コードの関連165テスト、59.590秒、全成功。既定入口が新engineを選ばないこと、max/private/hunter/9人fallback、被申告訂正取消での関係再生成・split、Name/表示率非依存、同周辺率で異なるjoint（C6対二つの三角形）の拒否、同groupに複数狼がいても独立化しないことを検査しました。公開／本人／stream／旧結果排除等の既存回帰も維持しています。

所有確認済18801を最終コードで再起動し、既定の通常UIもheadless Edgeで確認。通常7/15、roles→complete、計算中編集、入力保存、公開/本人切替、旧preview／本人応答排除が成功、JS例外0。UI機能は増やしていません。

残件は、一般の公開報告root、本人の最適化経路、max・狩人/GJ、一般7～9人、生成前からの圧縮、root行ベクトル自体のID輸送、既定有効化の判断です。今回全suiteを再実行したのではなく関連回帰であり、既知の予算文言テスト問題は別に残ります。保存形式・共有設定変更、push/deployなし。

測定: `benchmarks/player_match_groups/results.json`。再現: `python -B -m unittest discover -s tests -p test_player_match_groups.py -q`、`python -B benchmarks/player_match_groups/measure.py`。ログと画面は `.artifacts/player-match-groups/`。