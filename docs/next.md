# Next Restart Memo

## 現在地
このプロジェクトはいったん中断する。
現時点では、`parallel mode` を本線とした v1 の途中まで進んでいる。

できていること:
- FastAPI + Jinja2 + CSS の基本 UI
- Top / Main の画面遷移
- Tree の基本表示
- `進む / 戻る / tree click` の基本動作
- Vercel Hobby への deploy
- Supabase 接続と基本保存
- `core / modes / web` への構造整理開始

## 大きな難所
今回見えた主な難所は次のとおり。

- 人狼の公開情報盤面と内部確率状態のズレ
- parallel mode と full-tree mode の思想差
- CO / tactics 編集時の UX
- fork による世界線分岐と Tree 表示の整合
- node 移動と tree 編集をどう分離するか
- 全画面 reload による操作テンポの悪さ

特に、`CO / tactics` をどう編集し、どのタイミングで新しい node / tree を生成するかは未確定。

さらに本質的な難所として、各 player の視点差がある。

- parallel mode の思想では公開盤面だけで評価したい
- しかし実際には、狼の噛み先や占い結果の出し方は役職本人の private state に強く依存する
- そのため、正確さを追うほど「公開情報だけの盤面」では足りなくなる
- 結果として、`誰がその役職だったか` と `その時点で何を知っていたか` まで状態に持ちたくなる

この問題意識から `full-tree mode` の発想に進んだ。
ただし、全員分の視点・可能性・共有情報を同時に管理して全分岐させるのは非常に重い。


## 再開時のおすすめ順
再開するなら、次の順で考えるのがよさそう。

1. `parallel mode` を本当に完成させるのか、`full-tree mode` に早めに切り替えるのかを決める
2. `node移動` と `tree編集` を完全に別物として整理する
3. `進む / 戻る / tree click` を部分更新化する
4. その後に `CO / tactics` の UI / UX を作り直す
5. そのうえで v1 のロジック要件を再定義する

## 現時点の方針メモ
- `parallel mode`
  - ユーザーが盤面を入力する
  - `CO / tactics` は tree 編集寄り
- `full-tree mode`
  - 将来案として有望
  - ただし phase 設計と node 種別設計を先に固める必要がある
- 両モードは共通部品を共有しつつ、別モードとして持つのがよさそう

## 技術メモ
- Vercel は deploy 済み
- Supabase schema は作成済み
- `SUPABASE_DB_URL` は pooler (`:6543`) を使う
- `requirements.txt` は BOM なし UTF-8 にする必要がある
- Windows / PowerShell 経由の日本語ファイル書き換えでは文字化けに注意

## セキュリティメモ
この会話中で DB 接続文字列を貼ってしまっているため、余裕があるときに Supabase の DB パスワードは変更する。
変更後はローカル `.env` と Vercel の Environment Variables を両方更新する。

## 気持ちのメモ
このテーマは初心者向けというより、普通にかなり難しい。
今回の中断は失敗ではなく、難所を把握したうえで保存点を作った段階。
次回はゼロからではなく、この知見を持った状態で再開できる。
