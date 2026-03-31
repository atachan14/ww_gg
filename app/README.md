# app

FastAPI + Jinja2 ベースの現行実装をこのフォルダで進める。

## 起動
```powershell
uvicorn app.main:app --reload
```

## 入口
- `/` : Top
- `/main` : Main

## 構成
- `core/`: Shared Core。計算、データ構造、共通ロジック
- `modes/parallel/`: Parallel Mode 用の tree/state ロジック
- `modes/full_tree/`: Full-Tree Mode 用の受け皿
- `web/`: view model や tree 表示など Web 表示寄りの補助ロジック
- `main.py`: FastAPI のルーティング
- `persistent_tree.py`: 画面 tree から保存 record への変換
- `storage.py`: 永続化レイヤ
- `runtime_config.py`: 環境変数読込
- `settings.py`: 設定値・固定ラベル
- `templates/`: Jinja2 テンプレート
- `static/`: CSS
