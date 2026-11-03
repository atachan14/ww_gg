# 開発の手順

旧 `HANDOFF.md` と `AGENTS.md` を元にした手順。コードを変える前に、[PURPOSE.md](PURPOSE.md) とリポジトリ直下の `AGENTS.md`(計算の設計方針)を読む。

## 起動

- 作業場所: `G:\source\repos\Python\ww_gg`。
- `start.cmd` で起動する(リポジトリ内の `.venv` の Python、`-X utf8`、`dev_previews/run_current_app.py --port 18821`)。URL は `http://127.0.0.1:18821/main`。
- 新しい環境では、仮想環境を作って `requirements.txt`(Flask 3.1.2)を入れる。古いフォルダから `.env` や認証情報をコピーしない。
- サーバーを再起動するときは、今動いているプロセスとコマンドを確かめてから。古い記録の PID は今のものではない。

## コードの構成

| 場所 | 役割 |
|---|---|
| `app.py` | HTTP とストリームの制御 |
| `werewolf/` | 厳密な計算のモデル、盤面の移動、評価の記録、再構築 |
| `wwcore/` | 新しい計算の芯([redesign/core-v07.md](redesign/core-v07.md))。`/core` の画面だけが使う |
| `board_http.py`、`templates/core.html`、`static/core.js`、`static/core.css` | `/core` の画面(v0.8)。サーバーは Board ごとに計算するだけで状態を持たず、履歴はブラウザ内(IndexedDB) |
| `templates/`、`static/` | 画面の元のファイル |
| `public/static/` | ホスト用の静的ファイルのコピー。`build_vercel.py` で同期する(片方だけを手で直さない) |
| `tests/` | 独立した検証、契約のテスト、DOM のテスト |
| `dev_previews/` | 開発用の起動スクリプト、計測用のスクリプト |
| `benchmarks/` | 計測の結果 |
| `archive/` | 旧Python版・Java版・以前の試作 |

## 計算の設計方針(`AGENTS.md`)

- 製品のコードは、定義した式を計算する最小のアルゴリズムにする。
- 同値・対称性の前提と理由は、設計の文書に書く。
- 独立した列挙、反例、名前付きの結果の比較、cold での再構築の確認は、開発用のテストに置く。
- 外部入力の検証、支持ゼロの扱い、キャンセル、作業量・時間の上限は、それぞれ別の責任として持つ。
- 計算ごとに、変わらない入力とキャッシュを持つ。内部の子は共通の生成器からだけ作る。製品のループに、発行済みの台帳や証明のチケット、繰り返しの所有者確認を入れない。
- 確率・合法な行動・設定済みの方針・Q/P の更新・グループ分けの共通処理を使う。ケース専用の評価器を足さない。

## テスト

`tests/` に約300ファイル、約1650のテスト関数がある。全部を実行するのは重い(厳密な列挙を含む)。

1. まず小さい厳密なケースで確かめる。
2. 次に、影響する範囲の結合テストを実行する。

新しい芯のテスト(独立の数え上げとの照合。合わせて7分ほどかかる)は `tests.test_wwcore`。

```powershell
$env:PYTHONPATH='.;tests'
.venv/Scripts/python.exe -X utf8 -m unittest tests.test_wwcore
.venv/Scripts/python.exe -X utf8 -m unittest tests.test_core_http
.venv/Scripts/python.exe -X utf8 -m unittest tests.test_model_a_night_oracles
.venv/Scripts/python.exe -X utf8 -m unittest tests.test_browser_history tests.test_calculation_cancellation
node --test tests/personal_cold_generation.test.cjs tests/calculation_cancellation.test.cjs tests/browser_history.test.cjs tests/input_calculation_option.test.cjs
```

- 全部の実行(`python -m unittest discover -s tests`)は、コマンドごとに時間の上限を決めて、最終の件数とログを残す。一部だけ実行したものを「全部成功」と言わない。
- 重い探索を同時に走らせない。
- 期待値を今の出力に合わせて書き換えない。独立した計算(分数での列挙など)で確かめる。

## 公開

- v0.6 は未公開。Production(`03e4e31`)と Preview(`4dc7246`)は意図的に違う。
- **Preview のブランチに push すると、Vercel が自動でデプロイし、Team の利用量を消費する。** `master` への push は Production のデプロイになる。
- タグ、GitHub の Release、エイリアス、認証情報の変更は、ユーザーの承認なしにしない。

## 守るもの

`.artifacts/`(ローカルの進行記録)、ナビゲーションの再構築手順、未コミットの `docs/previews/`、旧版や復旧用のコピー、`.env`、関係のない編集。共有する docs に秘密や、実際の保存済み盤面の内容を書かない。
