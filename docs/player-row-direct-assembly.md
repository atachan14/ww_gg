# 行組立の単一経路化

基準 `96da610`。公開UIの旧dict組立→freeze→view経路を撤去し、`build_public_view` が既存のRoleState／Board／計算済み行値／正本ログから必要な不変行を直接作るよう変更しました。app側の二つの行loopはなくなり、各PlayerDataは直接作ったReadMapを読みます。`legacy`という内部field名とexportは互換の読み口であり、旧mutable rowが正本として残っているわけではありません。

本人側は既存APIとprivate cacheがdict JSON形を必要とするため、その境界を維持しました。`private_api_rows` にroles先行／完了の共通formatterを集約し、API dict→personal view→再exportという不要な往復を撤去しました。本人条件の検証・公開/物理分布の分離・Board ID/revision検査・browser世代照合は既存のままです。表示用のコピーを外したのであり、秘密条件の検証を外していません。

## 回数・コピー

計算段階ごとに必要なN行は各1回作ります。roles先行と完了は別の結果なのでそれぞれの生成が必要です。

| 経路 | 変更前 | 変更後 |
|---|---|---|
| 公開 | full legacy-row dict N個＋各行freeze N回＋不変行N個 | full legacy-row dict 0個・そのfreeze 0回、不変行N個を直接構築 |
| 本人API | 必要なJSON行N個＋view化freeze N回＋再export N回 | 必要なJSON行N個だけ、追加freeze/export 0回 |

これはfull-row変換の数です。RoleStateの周辺率dict、timeline、API内のprobabilities等、全てのPython dictが0になるという意味ではありません。公開の旧adapter／本人viewの互換import APIは明示的な読取・比較用に残しますが、通常UI/APIの行生成は通りません。実際のルートからそれらを呼ぶと失敗するmockテストを置いています。

## 有限の代表比較

表示組立だけを、5人／9人の固定した入力・計算済み表示値で比較しました。勝率solverや巨大な未来探索は走らせていません。各modeはfresh Python子、50回組立、3回、順序反転。tracemallocを含む時間なので、実画面の通常待ち時間や勝率計算の高速化率ではありません。

| 表示経路 | 50回の中央値 秒（前→後） | Python割当ピーク bytes（前→後） |
|---|---:|---:|
| 公開5人 | 0.10328→0.09882 | 203943→165012 |
| 公開9人 | 0.13004→0.12066 | 293410→207136 |
| 本人5人API境界 | 0.09725→0.00497 | 187096→7928 |
| 本人9人API境界 | 0.11683→0.00842 | 215543→13736 |

旧公開組立は96da610から固定したfixture、旧本人経路は同じ出力formatterに不要なview往復を付けた再現です。各比較の全出力行は一致します。新コードの組立回数・コピー数の変化を測るもので、旧commit全体と新commit全体のsolver性能比較ではありません。

この範囲で組立時間・Python割当ピークの悪化はありません。起動/importを含むprocess Peak Working Setも記録し、中央値は概ね29.7～30.0MiBで微小な増減がありました。プロセス全体のメモリが必ず減る、という保証ではありません。複雑な長期ログの全サイズを網羅した比較でもありません。

機械可読の全測定は `benchmarks/player_view_refactor/direct-row-results.json`、driverは `measure_row_assembly.py`。

## 最終検証

- 最終コードの関連124テスト、39.699秒、全成功。
- 96da610の旧行組立をtest fixtureへ固定。全field、manual timeline、Pending、合法手・零値・Noneの厳密比較。
- 旧full-row dictをfreezeしないこと、通常公開UIから旧row adapterを呼ばないこと、本人APIから不要なpersonal view/indexを作らないことを検査。
- 通常公開／本人、preview、roles先行→complete、Pending空行、訂正取消・過去編集、cache、cookie非変更の既存回帰を維持。
- 所有確認済み専用18801を最終コードで再起動。HTTP200確認後、隔離headless Edgeで通常表示7/15、入力更新とreload、計算中編集、旧preview排除、公開/本人切替、遅い本人応答排除を確認。JS例外0。最初の起動直後の接続拒否はready前の試験開始によるもので、HTTP ready確認後に完了しています。

ログと画面は `.artifacts/player-row-direct/`。全suiteを再実行した結果ではありません。既知の予算文言テスト問題を解決したという報告でもありません。

## 残す境界・残件

- JSON API・既存private cacheの形、旧保存読込、既存timeline生成器は互換契約のため維持。
- public_view／personal_viewの明示的な互換読取APIとto_legacy_row exportは比較・外部境界に残す。通常の行生成元にはしない。
- 公開indexの既存migrate/projectによる正本解釈は残す。そこまで変更すると保存所有・旧形式移行の別課題になるため、この差分で省略しない。
- 一致group計算接続、数学的最適化、旧保存形式撤去は未実施。名前編集や指標の意味変更なし。
- 現在描画するBoard/視点だけにviewを作り、探索全未来へUI情報を保存しない。第二の編集正本も作らない。

公開push/deployなしです。