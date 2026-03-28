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
- `main.py`: FastAPI のルーティング
- `view_models.py`: 画面表示用のダミーデータ
- `templates/`: Jinja2 テンプレート
- `static/`: CSS
