# コア向けHELP「プログラム詳細（仮）」の構成調査

調査対象: ローカルHEAD `97d0ed4`、実装基準 `eb8116d`。
読み取り調査と文書作成のみ。HELP実装・計算モデル・公開は変更していない。
既存の詳細レビューは [current-model-structure-review.md](current-model-structure-review.md)。

## 現在の配信と表示

| 経路 | 実装 | 内容 |
|---|---|---|
| `/help` | `app.py:393`, `templates/help.html` | 5人村の例・仕様の補足へのリンク。ゲームを変更しない |
| `/help/specs` | `app.py:396`, `templates/help_specs.html` | Jinjaの仕様補足。モデル、戦略、Pending等の説明 |
| `/help/five/` | `app.py:399`, `help_assets/tree-prototype.html` | 独立HTML。インラインSVG、段階表示、固定の5人村の例 |
| `/help/five/<name>` | `app.py:402` | 既存CSS/JSの許可リスト配信。一般の任意ファイル配信ではない |

Jinja側は `base.html` のヘッダー、`static/styles.css` と共通JSを使う。
入口は `footer_help.html` を各画面のフッターに挿入する。`navigation.html` は主に昼夜進行ボタンであり、
技術HELPの目次を足す場所は `help.html` が適切。既存2リンクのラベル・経路は維持する。

HELP用CSSは `.help-links` と `.help-specs h2/p` の小さな定義である。
MathJax、KaTeX、Mermaid、シンタックスハイライトライブラリの導入は現資産には見当たらない。
5人村の数式は分数と演算子の文字表示、図は手書きSVG、対話はローカルJSである。
静的ビルド `build_vercel.py` は `static` の第一者CSS/JSを `public/static` へコピーする。
新規CSS/JSを増やす場合は公開資産一致テストと配信設定も追随が必要。
HTML本文だけなら新しいクライアントJSは不要。

## 最小構成の提案

まず `/help` の既存2項目と並べて **プログラム詳細（仮）** を追加する。
技術入口 `/help/program/` から **プログラム詳細（現在実装）** と
**プログラム詳細（設計案）** へ分ける。入口には全体フローと読む順を置く。
`base.html` を継承し、HELPへ戻るリンク、説明対象版、現行／提案の表示を共通の冒頭に置く。
計算状態・セッションを変更するフォームやAPIは不要。

| ページ | 内容 |
|---|---|
| `/help/program/current/model` | 現在実装の確率モデルと情報集合。下記state/belief/historyの説明 |
| `/help/program/current/algorithm` | 現在実装の評価アルゴリズムと実装。policy/flow/continuation/cache |
| `/help/program/reference` | 型・関数・ファイルの参照表。主張の解説とは分離 |
| `/help/program/verification` | 再現例、式とfixture、テスト、不変条件、対応範囲 |
| `/help/program/design` | 設計案の入口。現構造を選んだ理由、提案の状態と対応章へのリンク |

説明（なぜ・どう考えるか）とReference（引数・戻り値・責務）を分ける。
最小の先行確認として1枚の入口＋ページ内目次から始める場合も、上記4分類のIDを先に固定し、
巨大な一枚本文を最終形にはしない。スラッグは登録済み章の許可リストで扱う。
関数1個ごとのページを最初から大量に作るより、処理責務単位の章＋関数への参照が読みやすい。
既存5人村サンプルは固定された能力なしの説明例なので、現在の一般solver全体を代表する図として流用しない。

## 具体的な目次とコード・テスト対応

| 章ID / 見出し | 型・関数・ファイル | 根拠テスト |
|---|---|---|
| `overview` 全体フローと評価の入口 | `app.replay/structural_replay`, `model_a_public.evaluate_public_game/public_forecast` | `test_public_model_a_ui`, `test_model_a_public` |
| `state` Board・役職世界・正確な重み | `exact.Board/initial_board/group_initial_board/replace_worlds`, `seer_acquisition.Hypothesis`, `TrueScanState` | `test_exact`, `test_group_model`, `test_public_prior_ownership` |
| `belief` 公開更新と本人条件 | `condition_claims`, `condition_private`, `prepare_public_prior`, `condition_guard_observation` | `test_private_view`, `test_public_night_row_normalization`, `test_guard_hidden` |
| `policy` 行動候補・情報集合・最大化 | `legal_targets`, `forced_action_worlds`, `score_day_targets`, `wolf_policy` | `test_information_set_model_a`, `test_wolf_view_forecast`, `test_guard_max_history` |
| `flow` 夜の順序とChance枝 | `NightFrame`, `FlowOutcome`, `resolve_action/action_flow`, `guarded_outcomes` | `test_action_flow`, `test_guard_effect`, `test_guard_history_flow` |
| `continuation` 公開更新・朝・次の昼夜 | `dawn.observe`, `InformationSetActionPolicy.project/morning_value`, `solve` | `test_dawn`, `test_morning_flow`, `test_information_plumbing` |
| `history` 三種類の分布と再開 | `PrivateView`, `GuardContext`, `seed_history`, `GuardHistoryMixture` | `test_guard_history_flow`, `test_guard_history_mixture` |
| `cache` メモ化・縮約・計算予算 | `value_law`, `project_evaluation`, `medium_value_key`, `joint_value_key`, `calculation_budget` | `test_mixed_flow_memo`, `test_evaluation_projection`, `test_information_set_model_a` |
| `verification` 不変条件と再現手順 | 上記テストの狙い、既知の対応範囲とPending | `test_help`, `test_deployment`, 関連DOMテスト |
| `design-review` 根からの伝播と途中Boardの再計算 | `current-model-structure-review.md` を基礎に比較 | ここは提案・未検証事項も含む。現行の保証と分ける |

各章を「入出力」「責務」「呼出元／次の処理」「守る不変条件」「コード参照」「根拠テスト」
の同じ構造にする。確率・情報集合の定義と具体的な関数名を併記し、抽象解説だけにしない。
公開 `s` の再投入は `scalar(private=s)`、`score_day_targets(private=s)`、
`wolf_policy` の公開 `s` からの `group`、`uncached_act` の物理Board再生成を明記する。

## 記法は現資産で扱えるものから

- プログラム: HTML `pre/code`。Jinjaの自動エスケープを維持し、横スクロールと長い識別子に対応。
  最初からコード強調ライブラリを必須にしない。
- データ構造・責務・不変条件: 表、定義リスト、型と関数のインラインコード。
- 流れ: 呼出順の箇条書きと静的SVG。図には代替テキストと同じ内容の文章を付ける。
  責務の概要図は1枚、手順はflowchart、主体間呼出はsequence、昼夜遷移はstateと用途を分ける。
  巨大な一枚図や全階層のC4図は作らない。Mermaidを採用する場合も元記法からSVGを事前生成し、
  閲覧時に図ライブラリを必須にしない構成が候補となる。導入はまだ行わない。
- 式: 単純な分数・総和・条件付き確率は文字と数式の意味の説明を併記。
  複雑な式が必要になればKaTeXのHTML+MathML事前生成が候補。元TeX、式ID、文章による意味を保持し、
  読み上げ・コピー・JSなし表示も考慮する。未導入の記法を表示できる前提にしない。
- 長い章: h2/h3と目次アンカー。折りたたみは補足・完全なログ・長いコードに限定し、
  主な処理フローをクリックしないと読めない構成にしない。

## 現行と提案を混ぜない表示

ページ冒頭に「対象commit」「公開版／ローカル研究版」「検証基準」を明示する。
本文を **現行実装**、**既知の制約**、**整理案・未実装** の区分で示す。
設計案もHELPの正式な説明対象として `/help/program/design` 側に置く。
現在実装と対応する章を相互リンクし、必要になれば `design/model`、`design/algorithm` 等へ分割する。
現在実装側には「なぜこの構造か／拡張意図」の短い説明を添え、その根拠文書と設計案へリンクする。
コードや既存文書に根拠のない拡張意図は、既存の事実ではなく今回の提案として明示する。
設計案は **提案中／採用済・未実装／実装済** を個別に表示する。
「採用済」は明示された合意を根拠とし、「実装済」は実装commitと根拠テストを示す。
実装済でも公開・ユーザー受入とは別の状態である。案の採否・承認日時を推測しない。
提案図は「案」とラベルを付け、現行呼出図と別図にする。
既存の `help_specs` は操作と仕様、プログラム詳細は実装の機構と根拠を中心にし、
同じモデル説明を二箇所に全文複製しない。仕様へリンクし、技術側では対応関数を説明する。
共通の記号・用語・不変条件・型定義・式ID・コード参照目録は一つの元資料に置き、
現在実装と設計案の両方から参照する。定義を変える設計案では既存定義を上書きせず、
「変更案」と差分を示す。案が実装されたら状態・対応commitを更新し、現行章へ接続する。

## ソースリンクの版

公開リポジトリは https://github.com/atachan14/ww_gg 。
原本のローカルremote参照と、公開commitページの両方で
`f348d7726f123cf6ce98764e0b88f4428b0ee362` の存在を確認した。
これは現在の復旧版より前の公開版で、最新公開HEADであるとの断定はしない。
検証したcommitページ: https://github.com/atachan14/ww_gg/commit/f348d7726f123cf6ce98764e0b88f4428b0ee362

ソース参照は `blob/<完全SHA>/<path>` を使い、行番号はその版から生成する。
公開 `master` とローカル現行コードを同一版として説明してはいけない。
未公開の `eb8116d` / `97d0ed4` はローカル参照として明示し、閲覧できる公開URLを捏造しない。
公開版向け解説とローカル研究版向け解説の参照を分ける。公開・pushはこの調査の範囲外。

## 更新・生成・検証の提案

最初は手書きの技術本文と小さな章目録で十分。文章自体をASTから自動生成する必要はない。
目録に章ID、対象ファイル、型／関数、根拠テスト、説明対象commit、現行／提案の種別を置く。
後にPython ASTで存在するシンボルと行番号を確認・抽出し、参照表を生成できる。
関数の挙動や意味論までシグネチャから推定して自動記述しない。
式ID→式の意味→関数→テスト・fixtureの対応表も目録に含める。
再現例はテストと共通のfixtureから表示用の正確な分数を事前生成し、本文の手打ち数値と
テスト期待値の二重管理を避ける。HELPアクセス時にsolverやテストを実行する方式にはしない。

将来、Markdownを本文の唯一の元資料にする場合は、開発時にHTMLへ変換してJinjaへ組み込み、
変換対象・エスケープ・許可HTMLを決める。任意のユーザーMarkdownやPythonをHELPリクエスト時に実行しない。
フローチャートの元テキストと生成SVGも対にし、差分検証できる形にする。
`vercel.json` は `docs/**` と `tests/**` を関数バンドルから除外しているため、
docsを実行時に読み込むMarkdownルートはそのままでは配信できない。
生成HTMLはテンプレート等の配信対象へ出力し、図・CSS/JSの配信先と資産検証を明示する。

追加実装時の検証は、既存 `test_help` と同じくGETによるゲーム状態不変、第三リンク、
目次アンカー、章の戻りリンク、許可された章だけの配信、参照シンボルとテストの存在、
コードのエスケープ、版の表示を確認する。CSS/JSを増やした場合は公開資産一致も確認する。
ブラウザでは狭い画面、長いコード、キーボード目次操作、JSなしで主要本文を読めることを確認する。

今回の確認: 既存HELPテスト6件成功。対応するルート、既存資料、配信構成を読み取り確認。
実装ファイルとHEADは変更せず、提案文書だけを追加した。
