# hash/物理盤面の後続試行（2026-10-17）

比較基準f3a12bdb150f0a6edde520314b561a1778ecac3cを維持。通常20秒/250000 work。旧深度走査hashと旧物理入力cacheは効果未確認で撤去済みであり、同じ案をそのまま再試行しない。

## 1. 検証済み配役を再走査しないBoard全hash memo — 撤去

既検証の3配役分布を除き、残りの全dataclass hash入力だけを初回に検査する候補。TrueScanStateは対象にしない。11境界回帰成功。7人/既存9人の交互3反復では、7人cold中央値13.153→13.144秒、CPU13.063→13.016秒、native peak186.297→188.910MiB。9人は4.279→4.316秒、CPU4.172→4.297秒、62.242→62.633MiB。全結果一致だが、一貫した時間改善を確認できずメモリ増のため撤去。差分・元コード・単体回帰は.artifacts/integration-validation/verified-board-hash-trial*へ保存。

## 2. 3配役分布だけのhash共有 — 検証中

Board全体のhashは保存しない。既検証の完全world/role/狼分布から、必要時だけ3フィールドのhashを求めて共有する。全dataclass hashフィールドを元の順で毎回hashし、その3フィールドだけを同じhash値を返す内部tokenに置換する。Boardの完全等値比較は変更しない。他フィールドは未知/mutable入力を含め毎回実値をhashする。型/履歴/視点/選択位置を同一状態へまとめる変更ではない。dataclasses.replaceで配役変更時は新しい検証済みsourceになり、他入力変更時は毎回の全体hashへ反映される。subclass/未検証配役は生成hashをそのまま使う。

11境界回帰0.006秒成功（全フィールド、配役/履歴/CO/報告編集、未知mutable、subclass、生成hashとの完全一致）。単発の通常予算対照は公開報告あり7人で候補13.186秒/CPU12.859、元hash13.355秒/CPU13.172、完全digest一致。native peakは候補187.805MiB/対照187.219MiB。採用未決、固定commit反復と全体回帰で判定する。

## 9人代表の範囲

全配役一様の9人seer-none probeは通常20秒でinformation_set_budget_exceeded。成功として数えない。別途、過去監査と同じCOグループモデルの9人seer-noneを選び、基準f3で503/1620・全9行・夜明け全9行を完成確認。これは占い非開示/未来取得なしの既存対応ケースであり、標準9人全能力の完成ではない。比較は同じCOグループ入力同士で行い、モデル変更をhash改善へ帰属させない。追加入力はboard_b_extended_cases.json。

## 物理側の観察

replace_worldsで完全worldからroleを先に射影し、能力ありBoardのconstructorがworldを正本として再射影している。重複算術削減の余地がある。ただし未知/mutable入力の互換を守る型検査と二重走査のコストもある。過去の全物理入力cacheとは異なる候補だが、現時点では未実装/未測定。
