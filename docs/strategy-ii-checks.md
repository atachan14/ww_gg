# 戦略UI②・本体接続

基準HEAD `0e31d62`。`.artifacts/ui-layout-gallery/overlay-2.html` 最新第3段は読取参照のみ。TOP・Board概要・共通情報行・表・公開Boardの厳密計算は維持し、MAINの戦略だけを選択中／未選択の分割Overlayへ置換した。

## 対応範囲

| 項目 | 本体への接続 |
| --- | --- |
| 盤面評価 | COグループ既定。初日昼・履歴なしでは全配役一様へ変更可。履歴がある場合は固定、既存Boardは保存モデルのまま |
| 村共通の吊り先・狼共通の噛み先 | max / randomの排他選択、既存Strategyへ接続 |
| 自噛み | 狼共通の行う／行わない。ゲームルールの許可がある場合のみ有効 |
| 村共通／各村役職のCO条件 | filled / counterの複数選択・OR。共通を継承し、個別では継承を無効化して別条件を追加可 |
| 狼の霊能騙り報告 | 狼の可能な結果騙り「すべて」の報告方針max / random。既存fake_reportsへ接続 |
| 騙れる役職 | 村役職なし、狼は配役内全役職で固定。自役真COは基底で許可。自役を追加候補から除外し、真Itemは変更不可 |
| CO後の霊能結果開示 | 将来の有効な報告機会は全開示固定。白のみ／黒のみは灰色、追加不可 |
| 真霊能の結果騙り | 不許可固定。追加候補は灰色、選択不可 |
| X日／黒X人のCO条件 | 灰色の見本。X値編集・追加・削除・Cancel復元はクライアント内だけ。resolver、ClaimPolicy、履歴へ送信しない |
| 追加役職能力・自由なfakeable／開示編集 | 未接続、灰色・固定。計算実装を追加しない |

自由なfakeable編集は内部引数だけなら可能だが、Board別保存・再生と未来の報告解釈までの整合が必要なため今回有効化していない。したがって実設定のallを削除・個別候補で置換する機能も固定。参照見本の自由なall／継承真CO編集を計算に無視させる接続は行わない。

## 保存・操作

薄いCOアダプターだけを追加。共通条件と個別のlocal／disabledを保存し、既存ClaimPolicyへ変換する。旧Boardでは村共通filledを表示基底にし、元の各役職条件との差を個別例外へ変換するので、条件・勝率を再解釈しない。進行時にCO編集構造を履歴へ保存し、戻るで復元。日夜評価・報告方針も従来のBoard別履歴を維持する。

陣営は初期展開、共通／各役職は初期折畳み。local Itemは存在すれば有効で削除のみ、継承Itemは削除不可でtoggle。外側は選択Itemを表示。Overlayは上部×なし・背景／Escで閉じず、適用／キャンセルで閉じる。footerは常時表示。詳細説明・有効無効status・未対応ラベルを増やさず、エラーと能力なし表示は保持。灰色X見本は再計算時も同じ画面のJavaScript内で保持するが、再読込やページ移動後の保存は保証しない。

## 検証

全86テスト合格。追加5件は旧条件の全組合せ移行、共通・個別例外、履歴保全と戻る、未対応／重複入力の原子的拒否、厳密値一致、旧モデル保持、初日モデル切替と進行後固定を確認した。

実Edge PC1280×1100／mobile390×1000で初期開閉、継承toggle／local追加削除、CancelとX値復元、灰色Xの計算送信隔離、真COと固定all／灰色候補、報告max/random、モデル・％分数、進行／戻るのFraction一致、mobile横はみ出しとfooter操作を確認。画像は作業workspaceの `strategy-ii-pc.png`、`strategy-ii-overlay-pc.png`、`strategy-ii-mobile.png`、`strategy-ii-overlay-mobile.png`。

8771へ反映しローカルコミットのみ。push・公開なし。archive・gg_ww2・Niixy・独立artifactは変更・コミットしない。

## 戦略の二重余白修正

基準HEAD `a38413c`。PC1280／mobile390の実DOMで、外側パネルpadding18pxに盤面評価padding13px・陣営枠margin10pxが重なり、左端からの距離が評価32px／陣営29pxになっていた（境界1px含む）。MAIN限定の2規則で評価paddingを `0 0 13px`、陣営marginを `10px 0` にし、両方19pxの一段へ統一。役職枠margin8px（境界込み9px）の階層字下げは維持。計算・状態・Overlayは変更しない。

実Edgeの同幅で修正後DOM値とPC／mobile画像を確認し、横はみ出しなし。画像は作業workspaceの `strategy-spacing-pc.png`、`strategy-spacing-mobile.png`。CSS限定のため数学テスト再実行は行わない。8771のCSS応答に反映済み。push・公開なし。
