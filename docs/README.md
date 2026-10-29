# ww_gg docs

人狼ゲームの期待勝率を厳密計算で求めるツールの docs。2026-10-29 に作り直した。

## 読む順番

1. [PURPOSE.md](PURPOSE.md) — 何をするツールか、守る原則
2. [STATUS.md](STATUS.md) — 版、できること、未対応のこと
3. [PERFORMANCE.md](PERFORMANCE.md) — 今いちばん解決したい「重さ」の問題と、これまでの経緯
4. 仕様(`spec/`)
   - [game-model.md](spec/game-model.md) — 役職、ルール、戦略、CO の条件
   - [screens.md](spec/screens.md) — TOP と MAIN、進め方、入力中の計算
   - [hosting.md](spec/hosting.md) — 公開環境、保存、計算の上限
5. [DEVELOPMENT.md](DEVELOPMENT.md) — 起動、テスト、公開の手順
6. そのほか
   - [USER_NOTES.md](USER_NOTES.md) — ユーザーに確認したこと
   - [QUESTIONS.md](QUESTIONS.md) — 確認待ちの質問
   - [HISTORY.md](HISTORY.md) — docs の経緯と旧資料の読み方

## この docs の書き方

- PURPOSE、STATUS、PERFORMANCE、`spec/`、DEVELOPMENT は、いつも**今の状態**に書き直す。古い記述に追記を重ねない(履歴は Git に残る)。
- `spec/` は「何を計算・表示するか(外から見た約束)」を書く。計算の内部の構造は、重さの改善で大きく変わる見込みなので、改善の作業と一緒に書く。
- 作業の記録や検証の細かい結果は、ここには書かない。
- 作り直しや大きな整理のときは、docs を消さずに `docs/archive/<日付>/` に移す。
