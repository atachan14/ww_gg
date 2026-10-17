# Board／PlayerData リファクタ：段階1・2

この文書は責務・正本・移行順の設計チェックポイントです。PlayerData の実装、通常UI接続、数理変更、保存形式移行はまだ行っていません。

## 1. 保存と比較基準

構造変更の基準は公開済み **03e4e31f965247da65a62386b8f38863459b5cc1** を推奨し、このbranchの出発点にしました。数学的な改善と構造整理の差を混ぜず、現在公開している挙動と比較できるためです。これは最適化試作を捨てる判断ではありません。

| 系統 | 固定点 | 今回の扱い |
|---|---|---|
| 公開版／queue修正 | 03e4e31 | 構造だけを変える主比較基準 |
| 不変な単一状態再利用 | e203aac | 独立した最適化比較対象。03との差は information_weights.py。後で同じ構造変更を適用して比較できる |
| browser固定5人 | 60fb7aa | Pyodide輸送試作。通常UI構造の基準にしない |
| browser QA・非最適化 | cb8ea84 | エンジン03。既存の比較記録として保存 |
| browser QA＋再利用 | 9dff55c | エンジンe203。7人有限計測・回帰記録を保存。公開版ではない |
| 枝内事前集約 | 3455e3a | 実盤面で組数が減らず不採用。移植しない |
| 生成前代表化 | 3e64635 | 生成単体では不採用。圧縮継続の否定ではない |
| 一致グループ圧縮継続 | c872d19 | 公開・均等・狩人なしの限定試作。通常engine未接続。構造移行後の独立検証対象 |

現在の計画branchは `refactor/player-view-stage12`、直前の全追跡内容は `safety/before-player-view-stage12-20261018`（c872d19）にも固定しました。各prototype branchはそのままです。trackedの未コミット差分は開始時点でありませんでした。

未追跡 `.artifacts/` 約474MB／24017ファイルはその場に保持し、全複製・Git保存したとは扱いません。`docs/previews/` 5件はSHA-256照合用一覧とZIPを `C:/Users/user/AppData/Local/Temp/ww-player-view-stage12-20261018/` に保存しました。reset/cleanや旧リポジトリ操作はしていません。

比較用の主要実装・既存fixture 20件のSHA-256を [baseline-manifest.json](../benchmarks/player_view_refactor/baseline-manifest.json) に固定。既存テストの宣言一覧は [existing-test-inventory.json](../benchmarks/player_view_refactor/existing-test-inventory.json)。宣言メソッド数は実行件数や網羅性を意味しません。

新規に公開基準で関連6モジュール・66テストを実行し、21.224秒、失敗0／エラー0でした。Board共有、履歴・訂正取消、cache、公開／本人stream、次の朝までの指標を含みます。今回の全suite再実行ではありません。過去のengine03系728件／e203系740件の全回帰には、既知の予算メッセージ期待値失敗が各1件あります。完全成功という基準には書き換えず、ログSHAと結果をmanifestに残します。

## 2. 責務と単一正本

- **GameData**：CastとGameRules。現行 `GameData`／`GameRuntime.data` の不変共有を維持し、各PlayerやBoardへ重複保存しません。
- **Boardの証拠・所有情報**：親、phase、現在までの全員共通の出来事、宣言変更、Board所有・世代・revision。現行保存入力とBoard graphから再構成します。
- **計算状態**：公開の共同分布、世界内秘密履歴混合、実際の物理分布と本人条件。Playerの独立確率の積に置換しません。
- **Board／視点のPlayer view**：個々のプレイヤーを読みやすく参照する、原則不変の行。正本の参照・派生結果を載せ、第二の編集可能な正本にはしません。
- **計算結果**：役職率、行の期待値、合法性、Pending等。入力・宣言ログとは別責務です。

`BoardData.players.by_id(1).co` や `BoardData.PlayerList.P1.CO` は読み口のイメージです。実際の命名・型はまだ導入していません。現行にも `app.py` が生成する `players` の行dictがあり、`id/name/claim/alive/status/役職率/action/by_dawn/timeline` を渡しています。新案は何もない所へプレイヤー情報を新規複製する話ではなく、その組み立て・責務を整理する話です。`archive/` 内の旧PlayerStateは現行の正本として再採用しません。

### Player項目対応表

| 提案項目 | 現在の所在・正本 | 新しい行での扱い／制約 |
|---|---|---|
| Index／ID | 1始まりのplayer ID、Cast人数、Board各mask・イベント | 安定した同一人物ID。配列添字やgroup代表IDに置き換えない |
| Name | `app.py` の `Player {id}` 自動表示 | 表示値として派生。自由入力名の保存・変更仕様は未実装／未決定 |
| CO役別宣言・訂正・取消履歴 | `public_log` のbatch/event、id/action/ref、Board所有元。legacy入力も残る | 正本イベントへの参照を役別に引く。Player別に並べ直した情報から全体順序を再構成しない |
| currentCO | `public_log_changes.declarations/project_changes` の有効申告から `Board.claims[id-1]` へ投影 | 派生値。CO切替後も元の取消・変更関係は残す |
| 公開能力結果（役別・日別） | 公開logのseer/medium申告、投影された `seer_inputs`／`reports`。計算には `SeerReport`／`MediumReport` | **公開申告**として参照。役・取得日・公開位置・元event IDを保持。独立の真実結果として保存しない |
| 真の取得結果／本人入力 | `Acquisition` と `Hypothesis.acquisitions`、本人 `condition_private` の結果、guard/attackの本人記録 | 公開申告と別領域。公開viewへ漏らさず、世界候補を一つの実際値に確定しない |
| 被公開結果 | 上記有効公開申告のtargetによる逆引き。専用の保存正本はない | 新しい**派生index**。宣言者・取得日・公開位置・元event IDを参照し、訂正取消で再生成 |
| 役職率／陣営率 | `RoleState.rates/probabilities`、本人は `private_role_rates`／private adapter | 視点別の計算出力。Fractionを維持。UIのcitizenとkernelのvillagerは明示adapterで対応 |
| 今日中の期待勝率 | 現行は `Forecast.by_dawn_values`／`HorizonValues`、行の `by_dawn` | 現行の正確な意味は「次の朝までの勝利質量」。最終勝率とは別。名称だけで今日中／日末へ意味を変えない |
| 最終期待勝率・行の値 | `Forecast.action_values`、private adapterの `final/dawn` | 行動介入の値であって、その人物固有の勝率と混同しない。どの指標・対象・視点かを付ける |
| 生死 | 実行済み観測、Boardの `alive/history`、Board graph edgeの観測・deaths | 有効な観測から派生。GJで死者を作らず、予定手を確定死亡として扱わない |
| 死亡phase／cause | `PublicEvent`／確定した履歴・graph edge。現行appはday→処刑、night→襲撃の表示を構築 | 元の観測を参照。表示文字列を解析して正本に戻さない。不明な原因を推測で埋めない |
| 合法手／選択中 | `legal_targets`、各行結果、draft/selection | 合法性はルール・視点から計算。draftと確定入力を混ぜない |
| 未計算／Pending／不整合 | `FuturePending`、予算診断、stream event、privateのNone/理由 | 数値0として埋めない。役職率だけ完了、最終値Pending等を指標ごとに保持 |

### Board／Game項目対応表

| 項目 | 現在 | 維持する責務 |
|---|---|---|
| GameRule／Cast | `GameData`／`GameRuntime.data` | Game共通の不変参照。変更は新しいGame世代 |
| phase／day／親 | `BoardFacts`、計算Board、`board_graph.nodes` | 入力Boardと計算投影Boardを区別し、親計算値を新しい証拠の正本にしない |
| 全員共通ログ・公開順 | batchのslot/mode、eventsの順、id/ref、Board所有 | simultaneousのまとまりと順序を保持。ただし記録順だけを新しい尤度・情報到着規則にしない |
| Strategy／CO方針 | 現在のBoard入力と各履歴stepのpolicy／claim_policy | GameRulesと異なり過去Boardごとに変わり得る。共通GameDataへ誤って固定しない |
| 公開Q／秘密混合／物理P | Boardのworlds/belief、TrueScanState、Action/ContinuationInputsのpublic/private/physical | 複数の意味を統合しない。Player行の周辺率は参照用の派生値 |
| 保存互換adapter | `BoardData.inputs/to_game`、public_log legacy/base/batchesとgraph | 旧形式を一気に撤去しない。現在は双方向投影があるため移行途中は既存入力契約を正本とする |
| cache／世代 | `GameRuntime`、BoardData.inputs、graph revision/input_revision、UI request ID等 | 数理cacheとviewの寿命を分ける。現在のcache keyを構造整理と同時に弱めない |

現在の `board_owned_log.prepare` はflat入力とnode.local_batchesを照合し、選択pathを再投影します。現時点で「graphだけが既に唯一の保存正本」と断定しません。段階3で書込窓口を一本化した後、flat形を互換投影へ降ろす順が安全です。入力形式撤去時期は保存互換の判断が必要です。

## 3. ここからの段階移行計画

| 段階 | 独立した変更単位 | 受入・停止条件 |
|---|---|---|
| 1（今回） | refs・未追跡成果物保護、公開比較基準とfixture/test所在の固定 | 既存変更を失わず、数理と試作の所在が再現可能 |
| 2（今回） | 上記責務・項目正本・未決定項目・不足テストを文書化 | 入力を二重管理しない設計。まだruntime/schemaは変えない |
| 3a | Board／視点に紐づくread-only Player viewを既存正本の上に追加 | 旧行dictと全項目・Fraction・None/Pending・公開/本人の一致。既存保存cookie/APIは維持 |
| 3b | 公開申告・被公開結果の派生index、全体順序と元event参照を接続 | 訂正/取消/過去編集・別枝で逆引きと有効COが正しく再生成 |
| 3c | UI読取を小さな単位で新viewへ切替、入力窓口を一本化 | 新旧HTML/JSON/stream・操作回帰が一致。数理入口は既存のまま |
| 3d | 重複した行dict組立・不要な内部adapterを撤去 | 全利用箇所が移行済み、保存互換と参照oracleを壊さない。古い全形式の即時削除はしない |
| 4a | 公開一致groupを計算層へ独立接続 | c872d19の限定均等ケースから。CO表示groupやPlayer周辺率だけで同値判定しない |
| 4b | 本人情報・選択対象・新観測による分割とfallback | 秘密の漏出、役職相関消失、誤った値のコピーなし。未検証max等は既存経路 |
| 5 | 構造単独／最適化単独／併用の厳密比較、UIと必要な全回帰、時間・メモリ | 未完了を高速化成功としない。公表／push/deployは別途で今回範囲外 |

段階3aはrequest/選択中Boardで作る軽いviewから始めます。全未来ノードにUI専用Name、timeline、逆引き、全ログを複製しません。数理の不変状態は既存のまま共有します。まず新しいview cacheを作らず、現在入力から再生成して寿命を明瞭にします。

派生値は有効なBoard入力snapshot・Game所有元・視点と本人証拠に紐づけます。取消訂正や過去Board編集では既存のinput_revision・子孫retirementに従って再生成。公開viewへ本人データをcacheせず、UIのrequest世代／board ID／revision照合も保持します。単なるPlayer IDやcurrentCOだけをcacheキーにはしません。

## 4. 既存の比較範囲と不足

既存テストの所在はinventory JSONに列挙しました。現在あるものと、今回新たに検証した範囲を混同しません。

| 既存の主な比較 | 所在例 | 新view移行で追加する必要があるもの |
|---|---|---|
| GameData共有、証拠再構成、旧replayとの比較 | test_board_flow、tests/fixtures/board_replay_v051.py | Player viewの不変共有・元入力非変更・全field比較 |
| Board所有・親子枝・訂正取消・世代retirement | test_board_owned_log、test_board_owned_future、test_public_log | 被公開結果indexとCO役別履歴が各Board/枝で再生成されること |
| 公開／本人役職率・能力履歴・相関 | private_view/private_adapter、seer/guard/information_set関連 | 公開申告と秘密取得の同日異内容、視点切替時の混入防止 |
| cacheの完了値のみ保存・分離 | test_game_evaluation_cache、test_public_support_cache | 新viewの寿命、staleな派生index、readonly行の誤変更防止 |
| roles先行→complete/error、古い応答拒否 | test_calculation_stream、既存browser記録 | 新旧row DTOの全field、各段階Pending・非対応指標、UI同値 |
| 期待勝率／次の朝まで／合法手 | test_by_dawnと各forecast/tableテスト | 新しい名前と既存指標の対応、個人固有の勝率と誤表示しないこと |
| 一致groupの厳密継続 | c872d19の別branch限定試作 | 通常経路への接続、viewの対称性を数理同値と誤認しないこと。max/狩人/一般9人は不足 |

全Playerフィールドを一つの正規化DTOとして新旧比較するfixture、被公開結果の訂正取消込みの逆引きテスト、Name入力仕様のテストはまだありません。今回それらを実装済みとは扱いません。数理の全回帰には既知失敗が残るため、構造変更のせいにせず、別問題として維持します。

## 5. 未決定のまま残す項目

- Nameをユーザー編集可能にするか、表示IDの別名だけにするか。
- 「今日中」が既存の次の朝までと同じ意味か。まず既存指標名を保持する。
- 不明な死亡cause・非対応能力役・未計算指標の表示契約。欠損を推測で埋めない。
- 旧保存形式をいつどのversionで読むだけの互換形にし、いつ撤去できるか。

これらは段階3以降に必要な時点で確認する事項で、今回新しい仕様として決定していません。構造変更と数理変更は別commit・別比較とし、巨大移行を一度に行いません。