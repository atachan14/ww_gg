# Hybrid Tableローカル完成（未公開）

基準本番aaf01473aeb321a7d48937c855f572954479b77d。独立UI領域、commit/pushなし。元の未来226テスト版は別領域のまま保護し、未来連携は専用の別worktreeで確認。

## 確定したUI

BoardTable直右に更新（未変更disabled、有効時強調色）とキャンセル（dirty時のみ表示）。COセルの直接selector、能力詳細は常時表示、CO追加行なし。dirty中は公開情報追加・既存LogItem編集/削除・次Board/戻る・戦略保存を無効化する。

下書きは確定状態との差分を末尾の仮simultaneous batchとしてprojectionし、180ms debounce後に全数値を再計算。中間編集を履歴へ追記しない。プレビュー表示とrequest_id/確定revision/AbortControllerで古い応答を拒否する。不成立/途中入力は入力待ちとして旧勝率・確率・狼数分布を現在値として表示しない。

更新は同じproposal関数で同じbatchを確定、プレビュー値と確定値一致。取消は仮batchを破棄して確定値と入力へ戻す。手動で同じ内容へ戻せばdirty解除（報告の入力順も正規化）。Enterで次Boardを誤送信しないよう編集selectは下書き専用formに関連付ける。

下書きはブラウザ同セッション内・同じ確定revisionで再読込復元。保存済みOverlay追加下書きもTableへ引継ぎ、旧二重下書きは取消して単一draftにする。確定Gameには混入しない。Overlay自体は維持。

## イベントとモデル

Table編集はassert/withdraw/changeを新itemへ追記。入力ミスは既存item訂正。CO撤回は対応する能力報告も同atomic batchで撤回。過去itemを残し、現在有効申告だけをTable/計算へproject。再COしても旧結果は復活しない。

安定宣言IDで後続変更を参照。過去訂正は宣言identityを保ち、参照不整合/参照元削除は全体拒否。旧v1/legacy保存を移行、順序不明を維持。戻るは後続batchを切り落として再projection。撤回済制約がhistory.claimsやseer_inputs経由で残らないよう初期priorから有効証拠でreplayする。

最新ユーザー承認：入力Boardのモデル化では現在有効な報告だけ使う。旧『P2を占った』を『P3を占った』へ変更したら、旧取得対象P2は探索開始ledgerから外し、P3を既取得とする。過去変更があるだけでは未来Pendingにしない。実際にP2を占った秘密履歴の復元は後回し。

これは実世界の取得を消したという主張ではない。過去宣言の由来はLogに残す。未来探索内に新しく生成した真の私有取得はhypothesis内で保持し、その後の未取得候補から除外し続ける。入力由来の観測prefixと探索内の実取得を分離した回帰を確認。

従来の霊能報告機会（CO前の結果を遡って取得しない）、初日ルール、手動真整合性/偽過去尤度一定、未来偽1人の均等 law は維持。複数偽の共同相関、未来CO戦略、狩人護衛/GJは未対応。予算超過・未来の当日必須報告不足はPending。

## 確認結果

Hybrid187件、統合236件成功。PC Edge 1440x1000でdirty即時数値、単一batch、確定前後一致、取消・手動revert・再読込復元、部分入力、遅延応答取消、変更で旧対象条件消去、CO結果同時撤回・再CO非復活を確認。追加EdgeでOverlay保存draft引継ぎ、非占い基本進行、事前霊能CO→翌朝結果、戻るで後続report batch除去を確認。

Evidence:
D:/CodexTemp/ww_gg-hybrid-qa-20261012/browser-final/hybrid-browser-results.json
D:/CodexTemp/ww_gg-hybrid-qa-20261012/browser-extra/hybrid-extra-browser-results.json
D:/CodexTemp/ww_gg-hybrid-future-qa-20261012/browser/hybrid-browser-results.json

試用：UI単独は python -B app.py --port 8785 --hybrid-table-preview。統合領域は同flagに --seer-future-uniform を追加。CLIの両flagは既定off。公開候補のwsgi入口はHybrid UIだけ有効化済み（未来はoff）で、承認後にこの独立差分を反映すればUIが有効になる。公開承認は別。
