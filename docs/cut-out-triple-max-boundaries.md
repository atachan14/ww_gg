# 昼max・夜max・偽報告maxを同時指定する境界

## 最初に止まっていた箇所と局所接続

c8437cc時点の比較用 `_reason` は `fake_reports=random` に固定され、三maxを指定すると `fixed supported uniform/full-disclosure configuration only` が最初の停止理由だった。人数・潜伏秘密・夜のprofile依存を判定する前の設定gateである。

今回、既存max比較のうち霊COがない場合だけ `fake_reports=max` をそのまま許可した。保存入力・Strategy・証明cacheのキーにもmaxを残す。内部でrandomに書き換えていない。霊COなし・途中CO方針なしという固定scopeでは、霊報告actionが発生せず、この設定は計算値を変えない。三つの設定値を保持できたことと、実際に偽霊報告を最適化したことは分けている。

## 現在の比較entry

すべてW1/H0で、通常UIへの採用ではなく初期snapshotの比較用入口。

| entry | 人数・配役/入力 | 昼/夜 | fake_reports=max |
|---|---|---|---|
| adapt_model_a | 4/5、M0/1、S1/2、従来の明示snapshot | random/random | 対象外、従来の均等scope維持 |
| adapt_max_model_a | 4/5、M0/1、S1真占1CO・初日白3、他は潜伏 | max/random または max/max | 霊COなしで許可 |
| adapt_latent_max_model_a | 4/5、M0/1、S1潜伏、初日なし/白、全潜伏または真霊1CO | max/random | 霊COなしで許可。霊COありは拒否 |
| adapt_terminal_night_max_model_a | 4、M0/1、S1、全潜伏、初日なし/白 | max/max | 霊COなしで許可。初回を外した3人夜は終局 |
| adapt_no_read_night_max_model_a | 5、M0、S1、全潜伏、初日なし | max/max | 霊COなしで許可。全候補のprofile読取なし完全証明が必須 |
| adapt_active_report_max_model_a | 4/5、M1/S1、霊CO1/2・他潜伏、初日なし/白 | max/max | 実報告の既存minと同点均等を接続。全候補の完全証明が必須 |

6/7人の別の均等比較scopeは変更していない。上表の入口でカバーできる例をつなげて一般対応と扱わない。

## 正式な設定項目の意味

`Strategy.fake_reports` は現行 `InformationSetForecast.generate_morning` の霊報告action選択に使われる。maxなら各偽色指示の完全な観測枝をcommon report_flowで評価し、村継続勝率が最小の候補を選び、同点は均等にする。worldごとの最適値を足す処理ではない。

占い偽報告は別項目 `fake_seer_policy` の `noncontradictory → uniform` に従う。`fake_reports=max` を指定しても、これを新しい偽占いmaxへ変更しない。今回の三maxケースでもユーザー初期の `Strategy()` と完全一致し、この占い設定を保持している。

## 4–5人の具体例と最初の残る停止理由

- **4人・全潜伏・M1/S1・初日白**：三maxを保持して終局夜entryで完全一致。公開方針による本人値1/4。本人の取得・終端履歴まで比較した。
- **5人・全潜伏・M0/S1・初日なし**：三maxを保持して読取なしentryで完全一致。全12襲撃候補は1/3、公開root/本人の公開方針評価は7/15。本人の占い対象介入も一致。
- **5人・真占1CO/白3・M1/S1、霊は潜伏**：既存情報集合max entryで三maxが一致。公開方針による本人値2/3。霊が配役に含まれても、霊COがなければfake_reportsの選択は発生しない。
- **5人・全潜伏・市民2/霊1/占1/狼1・初日白**：設定gateを通した後、読取なしentryの `five_player_no_read_requires_M0_initial_none_all_latent` で止まる。M1と初日白のjoint・本人履歴を、この限定夜max証明へ接続する部分が残る。近似や初日なしへの置換で通していない。
- **5人・霊COが2人、他は潜伏・W1/M1/S1、初日なし**：比較entryは `active_medium_report_max_outside_comparison_scope` で止まる。保守的に霊COが一つでも報告処理が発生し得るscopeを拒否するため、これは新しい未定義戦略を意味しない。

通常の完全潜伏root入口では、H0昼max/夜maxの対応判定が引き続き `root_secret_max_unimplemented` を返す。比較用originでの局所対応を通常UIの対応へ読み替えない。

## 実際に偽霊報告が発生する正式フローの対照

霊CO1/2、他潜伏の5人W1/M1/S1を正式に条件付けると6配役になる。三maxの完全root入口は `root_secret_max_unimplemented`。昼/夜をrandomとして偽報告maxだけを分離したroot_scopeも同じ未対応理由になる。

一方、既存common flowで処刑3・襲撃4という合法な外部指定actionを渡し、朝の生存1/2/5へ進めることはできる。これをroot全体の対応とは扱わず、既存報告戦略の局所診断に使った。霊1/2の偽色指示4候補を完全jointで評価し、`generate_morning` は両者白を質量1で選び、継続値は1/2だった。全候補値は保存JSONに記録している。これは既存の報告minの意味が定義されている証拠であり、新しい相互依存・解選択規則を足していない。

残る接続は、この報告最適化と潜伏秘密/観測の共同分布を、比較用の共通条件付け・評価経路とprofile証明のscopeへ受け渡す部分である。現時点で一般相互依存の解法完成、霊偽報告maxの比較entry採用、最適CO/偽占いmaxの追加は行っていない。

## 検証

`python -B -m benchmarks.player_match_groups.cut_out_triple_max_fixture`。三maxを保存した3比較、実報告対照、初期配役の停止境界を5 workerで検証した。完全Table、全選択/翌朝値、joint、本人介入、物理枝質量、取得/死亡/襲撃履歴、origin/cache読戻しを既存厳密参照・独立列挙と比較。既存53＋新規3の56回帰が成功した。

各worker60秒、評価25秒、証明12秒、全driver300秒、WorkingSet1,500,000,000 bytesの有限予算。開始checkpoint後の正確性検証中にMorishiの計測枠連絡を受け、既存runだけ完了させた。絶対速度測定や追加の大きなrunは行っていない。記録時間は予算内完了の確認だけに使う。

証拠は `benchmarks/player_match_groups/cut-out-triple-max-results.json`、ログは `.artifacts/triple-max-regressions-final.log`。公開・push・通常UI・サーバー変更なし。全project suiteは実行していない。

後続の限定接続: 実報告のある2霊COについては新しい明示entryを追加した。上記の旧独立entryの拒否と、通常rootの未対応判定は残る。現在の詳細と59回帰・候補/事後jointの照合は [cut-out-active-report-max.md](cut-out-active-report-max.md) を参照。
