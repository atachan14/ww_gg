# Player view / 被公開結果index：UI接続前チェックポイント

基準は `02a51fd`（runtimeは公開03e4e31）。新しい `werewolf/player_view.py` と専用テストを追加しました。app、templates、既存計算入口、GameData／BoardData保存形式は変更していません。通常UIから新moduleはまだ呼ばれていません。

## 読取入口

- `ViewScope.public(board_data)`：既存Board入力snapshot・revision・Board IDと、同じGameRuntime所有元に結び付いたスコープ。新しいGameや別snapshotを混同しません。
- `ResultFrame(scope, stage, request_id, reason)`：既存計算の段階とリクエスト世代。stageはroles／complete／pending／invalid。呼出側は実際の応答の来歴を渡す必要があります。このviewは計算や入力の真正性を独自判定しません。
- `public_view(board_data, existing_players, frame)`：現在の公開行dictを不変snapshotへ変換。`view.by_id(1).name/co/alive`、既存属性名、`player[key]`／`get`で読み取れます。
- `personal_view(public_view, existing_private_rows, private_frame)`：本人の既存行だけを別viewへ。`public.scope.personal(role, players, evidence)`で秘密条件のfingerprintを付け、公開フレームや別Boardの混用を拒否します。本人入力の生データはfingerprintから公開viewへ転記しません。
- `to_legacy_row()`：旧形式との全field比較・段階移行用の独立したdictを返します。元入力へ書き戻しません。

Nameは既存行の値を読むだけです。`by_dawn`は既存の「次の朝まで」の値をそのまま保持し、最終勝率への読み替えや今日中の再定義はしません。Fraction、文字列、None、既存Values／HorizonValues／ManualPendingを保持します。未知のmutableな行値や、公開行への本人専用field混入は拒否します。

view／行／ネストしたdict・listは読取専用です。旧形式exportを編集しても元のviewや入力は変わりません。これは表示結果の派生snapshotであり、第二の編集可能な入力正本ではありません。

## 公開申告のindex

`PublicIndex.from_board`は既存の `migrate/project/declarations` を使い、有効な公開ログを読みます。元のGame入力は変更しません。

- `events`：元event ID、action/ref、Board所有、batch、slot、simultaneous/singleとbatch内順序を持つ不変参照。
- `player.declarations`：その人の全公開宣言・訂正・取消。`co_history`はCOだけ、`published_claims`は有効なseer/medium申告だけを引きます。
- `player.received_claims`：有効な申告をtargetで逆引き。同じDeclarationオブジェクトを参照し、申告内容を別の正本へ複製しません。
- `current_co`：既存projectが出す有効CO。ログ履歴と現在値を分離します。

これは公開された申告であり、真の能力取得結果ではありません。`acquired_day`と公開の位置は別です。公開day/phaseは既存のreport_publications／所有Boardメタデータを参照し、legacyで順序や公開位置が不明ならNoneを保持します。記録順から新たな尤度を作りません。訂正取消や過去Board編集では、新しいsnapshotからindexを作り直します。以前のviewは不変なので過去の状態として残りますが、新しい結果と混同できません。

## 計算段階と古い結果

`player.metric(field, current_frame=active_frame)`はcomplete／pending／missing／invalid／staleを区別します。

- 入力・視点・本人条件・Game所有元・request世代が違う結果はstaleで、数値を返しません。
- roles先行やpending段階では、古いaction／by_dawn／dawn／finalが渡されても継続値として公開しません。役職率は別に完了できます。
- 既存Pending（ネストを含む）の理由を保持します。Noneを0や未対応と断定せず、計算完了frameで値が無ければmissingとします。
- factoryでも別snapshotや公開／本人フレームの混同を拒否します。同じ入力でもUI世代が変わる場合、次のUI接続で必ずcurrent_frame照合を行う必要があります。

Frameの所有元参照は内部の来歴情報です。view全体を汎用dataclass serializerでAPIへ出す想定ではありません。外部に渡すのは明示した行exportや指標だけです。既存公開／本人adapterで検証済みの行を渡す契約であり、任意の行dictの確率を再計算・検証するセキュリティ境界ではありません。

## 検証結果

- 新規11テスト、1.940秒、全成功。
- 既存関連94テスト、30.844秒、全成功。Board再構成・共有、所有履歴／過去編集、訂正取消、cache、公開／本人stream、次の朝まで、private adapter/viewを含みます。
- Flaskの実際のtemplate行と新公開viewの全fieldが往復一致。本人APIの全行も往復一致。
- roles先行、nested Pending、missing、別入力・視点・request世代・Gameでのstaleを確認。
- 申告訂正で旧targetの逆引きが消え、新targetへ移ること、取消、過去Boardへ戻ること、元の過去view非変更を確認。
- 実際の本人占い取得が公開の被申告indexへ混入しないこと、公開／本人の交互参照、元cookie／入力非変更を確認。
- legacyの未知順序を保持。view生成がroles()や評価を再実行しないことをmockで確認。

今回は全suiteを再実行していません。公開基準にある既知の予算文言テスト失敗は別問題として残しています。既存数学ファイル・app・templatesのbaseline hashが不変であることを確認します。ログは `.artifacts/player-view-stage3a/`。

## 次の小段階：UI読取切替の準備

1. 現在の `RoleState.owner` と同じ所有元・snapshotからscopeを作り、実際のroles/complete/Pending状態・run/request世代をframeへ渡す。別のGameRuntimeを作って同一Boardに見せない。
2. appの行組立完了後に、選択中Board／視点のviewを一度だけ生成する。templatesの書込やdict固有操作がないか個別に確認する。
3. まず公開行の読取だけを切替え、新旧HTML／JSON／roles先行出力を比較する。計算結果キャッシュや保存cookieは同時に変えない。
4. 本人行と逆引き表示は独立した次の差分にし、current_frame照合と公開への混入防止を維持する。新しい補足UIを勝手に増やさない。
5. 旧dict組立／export撤去は全利用箇所の移行後。旧保存形式の撤去は今回行わない。

新moduleにはグローバルview cacheや保存処理はなく、探索中の全未来Boardへviewをコピーしません。現行の共同分布・数理状態はそのままです。PlayerDataを確率独立化したり、一致group判定へ周辺率だけを渡したりはしません。通常UI接続、数理・共有計算変更、公開push/deployは未実施です。