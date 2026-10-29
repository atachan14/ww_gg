# Game / Board 並列設定 UI の確認

基準コミット: `7bf8a1a`。参照サンプルは `.artifacts/ui-layout-gallery/right-parallel-1`。サンプルと他の作業成果は変更していません。

## 反映内容

- TOP は配役とゲームルールを配置し、戦略と表示設定は MAIN に配置。
- MAIN は簡潔な配役行、幅420pxの概要、テーブル、右側の Game / Board 設定。設定を閉じるとテーブルが全幅へ広がり、開くと左側へ収まります。
- Game の表示・ルール、Board の戦略は排他的に開閉。設定の高さは概要とテーブルの下端までとし、長い内容だけ内部スクロール。
- 役職内訳は既定で表示。数値列は表示値から必要幅を求め、長い分数でも数値の重なりを防ぎます。
- 固定フッターに実際の Phase に対応する戻る・進む、概要・テーブル・Tree・全幅の操作を配置。
- 外側の戦略適用・取消ボタンは表示せず、その場で反映。Item 編集の適用・取消は維持。
- 自投票、棄権、占い師初日、狩人連続護衛はオプション全体を灰色・無効表示とし、計算には送信しません。未対応の選択値や既定値を有効な設定として扱いません。
- 自噛みだけは既存ルールへ接続。TOP で変更でき、MAIN は読み取り専用。許可時だけ戦略で行う／行わないを選択できます。
- 「判定」は処刑・襲撃直後の固定勝敗判定を意味し、可変ルールではありません。開始・勝利・判定の固定説明は通常画面から省略。Help は未実装。

計算エンジン・API・公開情報の意味・既存 Board の保存方式は変更していません。表示用ラジオは行動フォームから分離し、行動 POST に混入しないことを確認しました。

## 検証

- `python -B -m unittest discover -s tests`: 86件合格。
- JavaScript 構文確認、`git diff --check`: 合格。
- 実 Edge: 1440 / 1100 / 1040px × 設定4状態 × 内訳あり／なし × ％／分数の48ケース。横スクロール、数値の重なり、ページ幅のはみ出し、設定の重なりなし。設定の排他開閉と高さ上限を確認。
- Item 取消・適用、CO 個別例外、CO/霊能報告の即時反映・再読込、戻る時の対象復元、進むの連打、表示切替を確認。
- 5人の既存期待値 `7/15` と9人 CO 例の `94/315` を維持。
- 未対応ルールが disabled・name なしで送信されず、自噛み許可が MAIN に読み取り専用で引き継がれることを確認。
- 390px の縦配置、ページの横はみ出しなし、進むボタンの表示を確認。モバイルの詳細操作網羅は今回の範囲外。

今回の変更は UI のみで、9人の全履歴計算性能は再測定していません。既存の計算検証記録を参照してください。ローカルサーバー再起動時の cookie 初期化は既存動作です。

スクリーンショット: 作業フォルダの `parallel-top.png`、`parallel-main-board.png`、`parallel-main-game.png`、`parallel-main-full.png`、`parallel-top-rules.png`、`parallel-main-rules.png`。

起動先: http://127.0.0.1:8771/ 。push・公開は行っていません。

## TOP表示の追加整理

指定された「村の条件を決める」、TOPの「初期盤面の2段階比較（試案）」リンク、TOPの「公開情報から、処刑と襲撃の候補ごとに最終勝率を確認する。」補足を削除。見出しコンテナも除き、配役・ルールが自然に上へ詰まるようにしました。比較ページ本体・計算コード・READMEは変更していません。

関連既存テストはWeb14件、v0.3 14件、比較7件の計35件合格。独立EdgeでPC1100×1000の3表示消去、見出し余白除去、横はみ出しなし・開始ボタン表示、TOP開始→MAINの7/15を確認。画像は作業フォルダの `top-cleanup-pc.png`。8771の対象を照合してローカル再起動・反映済み。基準026492bの確認記録を保全し、push・追加公開は行っていません。


## ルール欄・1～2人の初期決着・MAIN表示整理（2026-10-09）

ルール欄は戦略と同じ team-section / scope-section / exclusive-field を使い、全体共通・村陣営・占い師・狩人・狼陣営を初期収納。余分な階層は追加していません。自噛みは不可/可能の単一選択、既存 allow_self_bite の真偽値・未送信false・旧1送信trueを維持し、新0送信もfalseとして受理。TOP編集可、MAINはdisabled/nameなし。未対応4項目は行全体を灰色、disabled/nameなし。

1～2人を正式に受理し、initial_board直後に既存 winner_for を適用する Progress.initial を導入。狼0なら村勝利、狼が村陣営数以上なら狼勝利。市民1＋狼1はDay1昼の初期決着、村0%/狼100%。行動・履歴を捏造せず、確率質量1を確定済みに移して保存復元。進む/戻る/対象未選択表示なし、CO・戦略POSTは決着画面へ戻り盤面不変。1～2人は5役職全20配役を確認。3～9人の従来の初期配役制約（狼1以上、村陣営が多数）と既知確率は維持。0/10以上、負数、非整数、能力役の過剰配役、余分な履歴は拒否。

ヘッダー人数を削除してバージョンだけ残し、TOP合計を「X人（最大9人）」として補足はsmall、入力に追従。合計・個別数・従来配役制約が不正なら開始ボタンを無効化、サーバー側も検証。

MAINのTOPへ戻る、全幅へ、比較リンク、共通補足footerを削除。ヘッダーロゴ、設定パネル収納による全幅復帰、概要/テーブル/Treeアンカー、通常盤面の前後移動、comparisonページ本体は維持。消した全幅ボタンのJS参照はoptionalに修正。初期決着のテーブル補足は「初期Boardの公開情報」。

検証: 全96テスト成功（約7.7〜9.1秒）、app.js/parallel.js構文とgit diff --check成功。既存3～9人、戦略、CO、公開配置相関、配信assets整合の回帰を含む。独立Edgeで自噛み0/1往復、全5accordion初期収納、42px選択欄、4未対応行、戦略との分離、保存・reloadを確認。PC1100px/mobile390pxで代表5配役の即時終局、分数切替・reload、連続submit、横はみ出しなし、0/10/3人不正配役の開始無効を確認。MAIN追加4削除とJS例外なしも確認。小人数以外の計算変更なしのため9人全履歴性能の再計測は今回実施せず、既存計算記録を参照。

画像・ブラウザ検証スクリプトは作業フォルダの rules-accordion-top.png / rules-accordion-main.png / small-cast-1100.png / small-cast-390.png / small_cast_qa.mjs。ローカル8771へ反映。README・archive・別gg_ww2・.artifactsを変更せず、push/公開は行っていません。

最終Edge確認で設定の展開→収納→全幅復帰、3アンカー、通常5人の昼→夜→戻るで7/15復元、ロゴTOP遷移、comparison GET200、補足12px/nowrapを確認。専用ブラウザを閉じ、実行中8771は最新状態を維持。


## MAIN配役サマリーの最小修正

実際の合計を先頭にして「9人村:市民4 · 霊能1 · 占い師1（能力なし） · 狩人1（能力なし） · 狼2」と表示。役職名と人数の空白・末尾の重複合計を削除し、能力なし注記と配役値を維持。TOP入力・TOP最大人数補足・計算は変更なし。通常9人と2人初期決着の表示を直接検証し、全97テスト成功（9.7秒）。専用Edge PC1100pxで実9人のサマリー・横はみ出しなしを確認し、cast-summary-pc.pngを作業フォルダへ保存。8771反映、README/archive未変更、push/公開なし。


## TOP補足2件の削除

「役職ごとの人数から合計を算出します。」と配役見出し右の役職列挙を削除。正常時のvalidation要素は空/hiddenとして余白をなくし、不正配役時の案内と開始無効は維持。全97テスト成功（9.8秒）、JS構文/git diff --check成功。実Edge PCで補足不在、合計入力追従、不正10人の案内/無効と正常5人への復帰、TOP→MAIN 7/15を確認、top-supplements-pc.png保存。検証assertions全成功後、Browser.close応答前に接続が閉じたためNodeはunsettled-await警告でexit1になりましたが、検証途中の失敗はありません。8771更新、README/archive未変更、push/公開なし。


## Footer遷移・実対象表示の統一

TOPの初日開始とMAINの前後ボタンを templates/navigation.html の小さな phase_button マクロに共通化。「Day1・昼へ →」「← Day1・昼へ」「Day2・昼へ →」形式。MAINの遷移先・履歴計算は従来式のままで変更なし。クリック時とライブ再計算後に別々の文字列を作っていた対象表示は updateTargetPreview に集約し、現在Phaseの「処刑：Player2」「襲撃：Player2」を表示。合法で選択済みの対象だけ表示し、random未選択は「処刑：未選択」、終局では対象欄なし。

Day1昼で履歴なしの場合「← ゲーム設定に戻る」を追加。1/2人の初期終局にも表示し、通常の過去Boardがある場合は従来back POST。新導線はHeaderロゴと同じGET /でありゲームをリセットしない。既存TOPは現在配役・ルールを再入力表示する実装ではなく、既定値（市民4/狼1、自噛み不可）を表示する。GETだけでセッションの盤面は消えず /main や /result で再表示できる。この既存仕様は変えていません。

狭い画面では対象をボタン上段に置き、戻る文言の途中改行を抑止。390pxで左右はみ出しなし、前後ボタン44pxを確認。

全98テスト成功（約10秒）、JS構文/git diff --check成功。最後のCSS調整後は配信assets整合を含むdeployment8件成功。実EdgeでTOP開始・連続submit、昼の手動Player2、エラー400で既存選択/Phase、戦略randomライブ再計算後の手動対象保持、夜の前後文言/襲撃表示、Day2昼の未選択、戻る、1/2人の初期決着、設定戻り→TOP既定値→保存決着画面への再表示を確認。ブラウザ例外なし。画像は作業フォルダ footer-night-pc.png / footer-day-mobile.png、スクリプト footer_qa.mjs / footer_mobile_qa.mjs。専用ブラウザを終了、8771へ反映済み。README/archive・別gg_ww2未変更、push/公開なし。


## TOPの現在設定復元・独立サンプルプリセット

承認範囲に限り、werewolf/setup.py に GameConfig（実配役＋Rules）と SetupDraft（TOP表示用の入力値）を追加。HeaderロゴとDay1設定戻りの共通GET /は、有効なGameの初期配役・ルールを復元。進行後の生存人数やBoard戦略/COから配役を作らない。初回/無効Gameは配役「5人サンプル」（市民4/狼1/その他0）、ルール「サンプル」（自噛み不可）。未対応4ルールは従来どおりdisabled/nameなし。

配役/ルールそれぞれ独立した選択欄。実数値・真偽値の完全一致で選択名を算出し、値を変えるとカスタム、元に戻すと自動復帰。人数の4.0/04等は整数4へ正規化し、非整数・範囲外・非有限値・不正表記は拒否。プリセットIDはフォームで信頼せず、実値から判定。実値は既存Gameセッションの人数/roles/rulesに保存し、プリセットの定義改定でも過去Gameを変更しない。

TOPフォーム編集中はGameを変更しない。不正POST400は送信draft（不正値を含む）を返し、既存Gameは維持。不正な自噛み値は選択欄に不正値として表示し、不可へ黙って置換しない。開始成功時のみ新Gameへ置換して履歴/CO/Board戦略を初期化する従来の開始動作。未開始draftはセッションやlocalStorageへ保存せず、TOPを再読込した場合は現在Gameの設定へ戻る。

ルール単体の既定値は従来Rulesに保持。欠落項目補完は setup.complete_rules に集約し、presetと保存値の双方からRulesを構築する。未知の項目/不正型は拒否し、意味が変わる将来の既存セッション移行はこの箇所でバージョン別に処理する想定。新ルール・大人数・新ゲームの実装はなし。計算モデル・厳密期待値・公開配置の意味は変更なし。

検証: 既存98件＋setup9件、全107テスト成功（18.3秒）。通常サンドボックスで既存tempfileテストの一時領域作成が失敗した回は、承認された検証権限で再実行して成功。JS構文/git diff --checkも成功。追加テストは両戻り経路/初回/無効セッション/独立preset判定/正規化/入力エラーdraftとGame保全/成功置換/配役・ルールpreset改定後の実値保全/欠落ルール補完/不正値拒否/1～2人初期終局を確認。

専用Edgeではpreset選択が互いに影響しない、実値変更→custom→再一致、accordion開閉で変化なし、ロゴ/設定戻りで9人＋自噛み可能を復元、未開始draftのreload、入力エラーdraft保持＋既存Game保全、正常開始時の置換、1/2人の決着→TOP復元、5人7/15・9人94/315の維持、専用ブラウザのcookie失効後サンプル初期化を確認。PC1100px/mobile390pxで横はみ出しなし、ブラウザ例外なし。画像は作業フォルダ setup-restored-pc.png / setup-restored-mobile.png、スクリプト setup_qa.mjs。8771は最新実装で起動、専用ブラウザは終了。README/archive・別gg_ww2・.artifacts未変更、push/公開なし。


## TOPプリセットのコンパクト配置

配役/ゲームルールの両プリセットを見出し行の右側に移動し、「プリセット：［選択欄］」の1行へ縮小。選択欄34px、文字12pxで従来の大きな独立行を削減。見出し行は必要に応じて折返し可能。selector ID/選択肢/値/JS判定は変更なし、名称相談に伴うリネームもなし。

設定9テスト＋配信assets8テストの計17件成功、git diff --check成功。独立Edge PC1100px/mobile390px/narrow320pxで見出し内配置・左右はみ出しなし・選択欄幅200px未満と高さ36px以下、配役とルールの独立選択/custom/再一致復帰を確認。ブラウザ例外なし。画像は作業フォルダ compact-presets-1100.png / compact-presets-390.png / compact-presets-320.png、スクリプト compact_presets_qa.mjs。8771反映、専用ブラウザ終了、README/archive未変更、push/公開なし。


## Game / Boardの5名称への統一

承認されたGameCast / GameRule / BoardOverview / BoardStrategy / BoardPlayerTableをTOPとMAINの見出し、GameCastの配役表示ラベル、ルール/戦略開閉見出し、Footerの参照導線へ反映。領域は見出しIDでアクセシブル名を参照し、MAINの配役/設定本文にはgroupを明示。接続用の既存DOM ID、CSSクラス、保存形式、URL、計算ロジックは維持し、見出し用の意味に合うIDのみ追加。役職ルール・戦略項目の一般名詞は変更なし。

直前の未コミットdocs/backlog.mdとdocs/requirements.mdの将来構想を保全して名称追加承認を反映。BoardInformationは不採用へ訂正し、将来のシステムログ表はBoardPlayerTable内のプレイヤー表の上に置く補足情報と記録。時点・未入力と不在確認・システム確定情報と申告の区別、パン屋の一般例は維持。システムログ機能の実装・特定プラットフォーム仕様の採用はなし。

全107テスト成功（19.7秒）。最後のアクセシブルgroup明示後はWeb18件成功、git diff --check成功。実Edge PC1100px/mobile390px/narrow320pxでTOP/MAINの5名称、ラベル参照、Footerアンカー、設定展開/収納、昼夜進行/戻る、既知7/15の維持、横はみ出しなし・例外なしを確認。画像は作業フォルダ names-top-pc.png / names-main-1100.png / names-main-390.png / names-main-320.png、スクリプト names_qa.mjs。8771で確認可能、専用ブラウザ終了。README/archive・別gg_ww2・既存.artifactsは変更せず、push/公開なし。


## 日本語の子ラベル・見出し統一・GameTree

追加訂正に従い、TOP/MAINのGameCast / GameRule / BoardStrategyの画面ラベルを「配役」「ルール」「戦略」へ戻した。見出し参照によるアクセシブル名も同じ表記。Game / Boardの親名称は維持で確定。内部DOM IDは変更せず、BoardOverview / BoardPlayerTableの表示名を維持。Treeは追加確定によりGameTreeへ変更し、見出し・Footer導線・aria-label・未実装の短い補足を整合。

BoardPlayerTable / GameTree見出しはBoardOverviewと同じ共通スタイルを適用し、文字11px・色var(--muted)・太さ/字間も一致。狭幅Footerは名称の長さに応じて折返し、既存ResizeObserverで実Footer高さを観測して下余白を追従させる。最下部のGameTreeが固定Footerに隠れないことをアンカー操作で確認。

関連40テスト（Web18/v0.3 14/deployment8）成功、追加GameTree後Web/deployment26件と最終余白調整後deployment8件を再確認。JS構文/git diff --check成功。独立Edge PC1100px/mobile390px/narrow320pxでTOP/MAIN日本語表記、維持した親名称、GameTree見出し/導線/アクセシブル名、3見出しの計算済み文字サイズ・色・太さ・字間の一致、Footer/設定収納/昼夜進行と戻る/7/15/横はみ出しなし・例外なしを確認。GameTreeアンカーでパネル全体がFooterの上へ表示されることも確認。画像は作業フォルダ labels-top-pc.png / labels-main-1100.png / labels-main-390.png / labels-main-320.png、スクリプト labels_qa.mjs。

要件基準・backlogへ最新の名称訂正と、固定配役人数・ルールのゲーム全体の分岐を整理するGameTreeの将来意図を追記。Game→Session案は不採用、Game維持を確定として記録。GameTree本体・システムログ機能は未実装。8771反映、専用ブラウザ終了。README/archive・別gg_ww2・.artifacts未変更、push/公開なし。


## 単独CO詳細行と霊能入力（2026-10-09）

従来の霊能結果欄は表の下にあり、処刑前CO・翌日昼までの生存・報告機会という条件を満たす場合だけ表示された。Day1や夜には入力欄がなく、基本行のCO表示から結果欄を開く導線もなかった。今回、基本行を表示用COボタンに置き換え、展開した役職行に日付順の結果を置いた。旧独立パネルは削除した。入力名・公開報告条件・厳密計算・保存形式は変更しない。

全116テスト合格（19.626秒）。追加9件では一人一CO、Day1なし、夜の予告、Day2白黒・未入力、黒入力後の狼確率1、途中COの遡及禁止、CO削除後の報告と履歴の保持、再設定、終局時の読み取り専用表示、未実装役職を検証した。JS構文・git diff --checkも合格。計算モデルは変更していないため、9人全履歴の性能再測定は今回行っていない。

独立EdgeのPC1100px/mobile390pxで開閉・追加・削除・一人一CO・連打・結果変更の最新値反映・白黒と厳密計算・Day1〜3の日付順・戻る・役職確率表示切替とcolspan・途中CO・占い師/狩人の能力未対応・横方向の結果閲覧を確認した。基本行40px、宣言行と追加行36px。ページ全体の横はみ出しと実行時例外なし。作業フォルダの co_details_qa.mjs、co-details-pc.png、co-details-mobile.png に確認資料を残した。8771は更新済み、専用ブラウザは終了。README/archive・別gg_ww2・既存.artifactsは未変更、push/公開なし。


## CO詳細スリム化の検証（2026-10-09）

全118テスト合格（24.114秒）。追加2件で宣言行のテキスト化とhiddenの単独CO送信、未COの表示文字除去、表示専用ゲーム識別子のBoard間維持・開始失敗時維持・新ゲーム時更新・計算gameへの非混入を確認。既存の霊能結果と厳密確率、削除後の報告保持を含むテストも合格。JS構文とgit diff --check合格、静的配信資産を同期済み。

独立Edge PC1100px/mobile390pxで枠なしCOボタン、役職セレクターなし、宣言/追加の同じ28px行、追加削除と連打、霊能結果変更と厳密値、Day1〜3の履歴、次Boardと戻るの展開維持、新ゲームの全収納、表示切替、ページの横はみ出しなしを確認。標準buttonはEnterで収納、Spaceで展開しフォーカスを維持。CDPの最初のEnter試行は文字入力指定不足で失敗し、Enter文字イベント付きで再実行して合格。能力結果・計算の変更はない。

資料は作業フォルダ co_slim_qa.mjs / co-slim-pc.png / co-slim-mobile.png。画像を目視確認、専用ブラウザ終了、8771更新済み。README/archive・別gg_ww2・既存.artifactsは未変更。push/公開なし。
