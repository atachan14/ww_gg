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

## 後続の採否と単一lookup候補

3分布prehashの固定版5反復40リクエストは全完成・結果一致。7人cold中央値13.297→13.161秒、CPU13.094→12.938秒、peak187.602→189.391MiB。9人は4.323→4.294秒、CPU4.281→4.281秒、63.488→63.766MiB。時間差が小さい一方で保持量と実装が増えるため、今回は撤去した。試行commit7cc3098は履歴に残し、検証テストを.artifactsへ保存。

物理二重射影の削減も11単体回帰を通したが、単発で13.454秒/CPU12.938、基準13.504秒/CPU13.047、peak差約0.06MiBと小さかった。通常の揺らぎと分離できず未採用。差分・テスト・probeを保存して撤去。秘密仮説だけのconstructor証明つきhash memoは5回帰を通したが、単発CPU13.156対基準12.875、peak約7MiB増で撤去。過去の全State深度走査とは違う方式だったが、有効とは確認できなかった。

導入済みPythonのFraction.__hash__は内部_hash_algorithmを16384件LRUで既に再利用していた。次は新しいhash/cacheを足さず、既存cacheの「key in cache→cache[key]」をsentinel付きgetで1回にする候補。完全キー・値・公開/本人境界・ヒット時tick・失敗時非保存・FIFO/容量は変更しない。対象はcached_flow/public_support/values/policies/既存action hit。falsey値・無効化・失敗・予算tickを含む5回帰0.000秒成功。最初の予算テストはAPIが受け付けない0を指定したため、合法な1を先に消費して同じ既存tickを検証する形へ修正した。

単発は候補13.180秒/CPU12.922、基準13.090秒/CPU13.016、peak約0.43MiB減で、採用判断には反復が必要。最初の置換スクリプトがassertで未適用だった2probeはinvalid-no-editとして隔離し、改善の証拠に数えない。現在は正しく適用した候補だけを反復・全回帰で評価する。
