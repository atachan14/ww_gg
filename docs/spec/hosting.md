# 公開環境・保存・計算の上限

根拠はコード(`wsgi.py`、`app.py`、`vercel.json`、`werewolf/calculation_budget.py`、`werewolf/browser_history.py`)と旧 docs の検証記録。

## 3つの環境

| 環境 | 版 | 内容 |
|---|---|---|
| Production(https://ww-gg.vercel.app/) | v0.5.2(`03e4e31`) | 公開中の版。`master` ブランチ |
| Preview(Vercel) | `4dc7246` 系 | v0.6 の検証用。ブラウザ内の履歴保存と、永続する Tree を有効にしている(`VERCEL_ENV` が preview のときだけ) |
| ローカル | 作業中のブランチ | `start.cmd` で起動。`dev_previews/run_current_app.py` が開発用の入口 |

- Preview のブランチに push すると、Vercel が自動でデプロイし、Team の利用量を消費する。
- Production の既定では、Tree の閲覧は無効(ホスト環境で有効にすると拒否される)。

## 保存

- ローカル: 進行の記録を `.artifacts/navigation` に保存する。消さない。
- Preview: ブラウザの IndexedDB に、署名付きの「再構築の手順」を保存する。サーバーは手順を検証して、同じ計算器で再生する(ブラウザ側の確率は信用しない)。同じブラウザ・同じオリジンの中だけで有効で、端末をまたぐ同期はない。デプロイの URL ごとに保存場所は別。
- 共有データベースはない。

## 計算の上限

- アプリの協調的な上限: **270秒 / 400万 work**(`werewolf/calculation_budget.py`)。Vercel の関数の上限は300秒(`vercel.json`)。
- 上限に達したら「未計算」で、確定した値ではない。時間と作業量のどちらで止まったかを分けて表示する。
- キャンセル: 明示的なキャンセルで計算を止められる。ただし、キャンセルの登録はプロセスの中だけなので、別のサーバーで動いている計算を確実に止めることは保証していない。
- 実際の Vercel 上で、270/300秒の時間切れと再試行、通信の切断からの再試行は、まだ確認できていない([../STATUS.md](../STATUS.md))。
