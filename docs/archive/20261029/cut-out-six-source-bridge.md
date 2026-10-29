# 固定CO・第一夜後のsource群保証checkpoint

[設計案](cut-out-six-source-bridge-proposal.md)の第一段階を明示的な比較入口として実装した。通常UIや既定のSixInputRegistry/current_screenのroutingは変更していない。重い比較前のコード・軽い正しさcheckpointである。

## 明示入口と範囲

`cut_out_six_source_bridge.issue(registry)`で保証を発行し、`screen(registry, witness=...)`または`read_action(registry, witness=..., target=...)`に渡す。未発行/未束縛ならunsupported。保証の永続化・別プロセスへの流用はせず、保存入力を読み直した場合は再発行する。

既存6人W1/S1/H0・均等・初期random_whiteの最小2形状、固定CO、保存された初日処刑＋第一夜死亡後のDay2/dayだけを受ける。現在sourceから先の既存均等継続は共通flowを使う。group Model A、information-fixed/compatibility、full-observed設定を維持し、過去stepのstrategy/claim policyも同じscopeであることを確認する。途中CO/CO撤回、初期報告変更、未知モデル/演算、max、7人、狩人/GJ等はunsupported。

## 発行根拠とsource結合

`replay_root_secrets`に結果を変えない観測専用フックを追加した。既存初期群を一度だけ用意し、初期・公開snapshot・保存行動の完了・最終sourceの7境界から保証を組み立てる。保存夜については既存の方針尤度によるPの混合とQ復元が終わった後のbranchを受け取る。保存観測を行動介入へ置換せず、数値計算/条件付け/方針はそのまま。

発行前にreplay結果の公開Board/Q、physical Board/P、past、observerをSavedOrigin(project_public=False)の現在sourceと完全比較する。Qだけの一致や周辺配役の一致では発行しない。群は親群から新しい死亡/公開報告端点を分割するだけで、lawから置換群を探索しない。

保証をメモリ内の発行台帳でobject identityに結び、registry、BoardData、SavedOrigin、初期spec、入力digest、global revision、Board ownerのrevision/input_revision/generation/branch、完全sourceに束縛する。コピーで作った未発行保証、同内容でも別originのregistry、owner経路と保存historyの不一致は拒否する。revisionは非負の整数（bool/float/string/null不可）で、現在ownerのinput_revisionとの一致も要求する。これは限定scopeの整合性gateであり、任意の外部履歴lineageを推測して認証するものではない。

新engineは発行済みcontext列を継承registryへ登録して開始する。既存SimpleNamespace/start().groupsを証明として取り込まず、各枝で初期adapterやroot+全履歴群を再構築しない。保証を持たない時に旧照合や均等補完へ戻るfallbackはない。

## 編集・取消・本人情報

現在の報告を編集・取消・再入力した場合は新registry/originから再発行する。数値が元通りでも以前の保証を新snapshotへ流用できない。古いsnapshot自体はimmutableのまま、そのsnapshot用の保証で読める。actor/frameの別入力へのstale判定も維持する。

公開Qと観測由来Pを分けたまま共通Tableを作り、本人role/resultsは既存OwnViewで別条件付けする。本人情報を公開方針へ混ぜない。個人枝のmassは実際のphysical carrierから求め、Qで置き換えない。cold replayは保存入力から再構築し、完全なQ/P/past/physicalと比較する。

## 軽い検証

最終4ケース（公開/本人source、編集・取消・再入力、拒否、霊能CO）＋関連8回帰が12.468秒で成功。数値ケース最大1.406秒、PeakWorkingSet最大39,419,904 bytes。worker60秒/RSS1.5GB・driver120秒の制限内。

- Q≠Pの実例で公開/本人Table、Forecast、primary/cumulative、joint、個人枝mass、cold復元を旧root群・旧全ラベル参照と比較し一致。
- 7 replay contextでQ/P両carrierを保つ交換16件を検証。
- 新経路の発行・再帰評価・coldでcanonical/CandidateRules0。screen/枝評価中に初期adapter・旧current群の取り込み・旧root群再構築を呼ぶと失敗する監視も成功。
- 編集・取消・再入力の3snapshotで再発行。古い保証の流用を拒否し、redoで数値が同じでも別originが必要。元snapshotと旧frameのstale判定を保持。
- 未束縛、未発行コピー、P/physicalのQへの差し替え、負/bool/float/string/null/owner不一致revision、未知モデル、owner path不一致、同内容別origin、CO撤回を拒否。
- 既存の保存夜尤度がPだけを変える回帰、報告編集/cache再構築、秘密支持ゼロのPending、6人二夜初期入口の回帰を確認。

結果とsource SHA256: `benchmarks/player_match_groups/cut-out-six-source-bridge-results.json`。軽量log: `.artifacts/six-source-bridge-light.log`。比較は小さな正しさ検証に限り、全project/重いaggregate/反復速度測定は行っていない。

保証発行には初期adapterと保存replayの追加計算がある。前段の初期6人増分群方式が旧root群より7〜8%遅かった事実は維持し、本bridgeの速度改善は主張しない。広いCO編集や履歴scope、通常UI採用、性能の追加検証は次工程。
