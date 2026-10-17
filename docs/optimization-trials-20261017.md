# 2026-10-17 軽量化試行

比較基準は1604a62867ba047806a06cd62e43b261178e1e06。前回の通常予算140件・全681テスト・HTTPの証拠は変更しない。各試行は通常20秒/250000 work、厳密結果と公開/本人分離を維持する。性能は初回/繰返し・CPU・native全worker peakで比較し、無効な候補は製品へ残さない。

## 試行1: 追加prefixの撤去

仮説: 前回CPU改善が一貫せず約2MiB増えた追加prefixだけを外すと、完全履歴/既存step再利用の意味を保って保持量を減らせる。

GeneratedBoardの親参照・完成結果・適用可否memoを撤去し、完全なorigin/historyを毎回辿る。既存step/kernel再利用、snapshot所有権、dataclasses.replaceで編集時memoを初期化するinit=Falseは維持。再構築入口のtick(0)で期限検証を維持する。64レシピ・分岐・履歴編集・秘密兄弟・親を保持しない所有権・失敗・期限・Game cacheの26回帰が11.522秒で成功。最初の単独実行は存在しないtest_game_runtimeを指定したimportエラーであり、正しいtest_game_evaluation_cacheへ直して成功した。ログはいずれも保存。

この保存点では正式時間比較と全体回帰は未実施。速度改善済みとは扱わない。過去のprefix実装/比較記録は履歴として残す。
