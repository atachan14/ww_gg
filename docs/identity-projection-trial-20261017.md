# 同一共同分布への射影再構築削減（2026-10-17）

基準は f3a12bdb150f0a6edde520314b561a1778ecac3c、候補は 1354022。
全回帰・専用18801 HTTP確認後に採用。push/deployなし。

## 調査と変更

通常予算の別診断では project_private 8,636呼出しのうち5,102回が非周辺化かつ公開配役重み不変（計13,794 hypothesis）。全47,990 hypothesisが省略対象という意味ではない。既存profileでproject_private累積2.47秒、TrueScanState構築31,416回だった。診断値は速度測定と分ける。

project_privateは元の完全履歴と同じ配役重みへ射影する場合、厳密な不変型・正規化順序・重複なしを検証できれば既存TrueScanStateを返す。完全キーは役職/全占い取得/全護衛/全襲撃。役職周辺分布だけで秘密履歴を同一視しない。全質量は既存コンストラクタによる正のFraction・総和1の検証が、不変入力に対して保持されていることを利用する。元の質量演算 q×new/old=q、normalizeも順序・各完全キー・質量を変えないので、全履歴と観測prefix/roster/tracked/初日規則を保ったまま再構築を省ける。

重み変更、周辺化、重複/未整列、可変入力、サブクラス、非厳密対象質量は従来の構築・検証経路を通る。型のフィールドが将来増えた場合も従来経路へ戻す。新キャッシュは静的dataclassフィールド照合だけ（maxsize=1）で、局面・観測者・秘密・事後分布を格納しない。Model A/秘密混合/物理枝質量、観測条件、合法手、設定方針、maxや予算は変更しない。

## 通常予算5反復

freshプロセス、直列AB/BA、cold+warm各1、250,000work/20秒。40/40完了・意味digest一致。数値113/504（7人全7候補とP2/P3各1/2）、503/1620（9人全9候補）を確認。

| cold中央値 | 基準wall→候補秒 | CPU秒 | whole-worker peak MiB |
|---|---:|---:|---:|
| 7人・観測あり | 13.9776→13.1623 | 13.46875→12.9375 | 187.809→182.168 |
| 9人・占い取得なし限定 | 4.3100→4.1967 | 4.234375→4.15625 | 63.469→61.793 |

7人wall IQRは0.579→0.376秒。背景負荷>10%も除外せず保持。低負荷のみ7人は基準1回/候補2回で13.447→12.888秒、9人は各4回で4.301→4.204秒。小標本のため別の保証とは扱わない。warm中央値は7人0.0160→0.0153秒、9人0.0653→0.0649秒で大きな変化なし。メモリは起動・出力・cold+warmを含むプロセスピークで、局面単体の割当量ではない。

9人はCO-group/占い取得なし・護衛なし限定ケース。通常9人の全能力/全max対応や異なる背景負荷への保証はしない。前候補single-lookupの全回帰予算失敗は別記録として保持し、この候補の効果や背景負荷へ原因帰属しない。

## 検証

新規単体7件成功。未整列/重複の正規化、同じ配役で異なる秘密履歴、再重み付け、周辺化、観測prefix、可変metadata再検証、サブクラス、float対象質量を元実装と比較。混在cache 88評価・共同分布/本人観測8評価も不一致ゼロ、入力不変・未対応Pending維持。全694回帰が379.410秒で成功（exit 0、OK）。所有コマンドを照合して専用18801を再起動（PID22836）。実HTTPは7人113/504が15.183秒、9人限定503/1620が5.371秒、本人5/6・1/6/セッション不変、4画面・HELP200・overflow/JSエラーなし。HELP更新後の表示も確認。

構造化証跡: benchmarks/results/identity_projection_20261017.json。各試行の時間/CPU/背景負荷/ピークと全数値参照を保持。

最終検証証跡: benchmarks/results/identity_projection_20261017_validation.json。全回帰ログとcache/joint summaryのSHA256を記録。通常UIへの補足追加なし。

再現: `python -B benchmarks/board_b_benchmark.py run --output <output> --repeats 5 --cases benchmarks/board_b_extended_cases.json --select seven-observed,nine-seer-none --board-before-ref f3a12bd --improved-ref 1354022`。同出力snapshotsに対してboard_b_cache_audit.py / board_b_joint_audit.pyを`--versions new,improved`で実行。全回帰は`python -B -m unittest discover -s tests`。重い実行は直列。
