@AGENTS.md

# Claude Code 向けの入口

- プロジェクトの docs は `docs/README.md` から読む(目的・状態・重さ・仕様・開発手順)。
- ユーザー個人のナレッジベース `G:/kb` の運用方針と目次は、セッションの開始時に自動で読み込まれる(ユーザー全体の設定の SessionStart フック)。ww_gg の案内は kb の `development/ww_gg`。
- このブランチを push すると、Vercel の Preview が自動でデプロイされる(`docs/DEVELOPMENT.md`)。
