# 夜の行評価・本人視点・死体フラグ・Overviewの現状

2026-10-13。ユーザーの指摘は、行に常時表示する仮想対象の値と死体フラグを混ぜず説明すべきというもの。前の二択への承認とは扱わない。

| 箇所 | 現在 | A統合で変わる箇所 |
|---|---|---|
| 全体のP3行 | フラグなしでもP3を対象にした最終値/期限内値。公開旧solverの指定行動法 | 表示の意味・操作は維持。モデルAの合法な物理分布と後続方針で計算するため値は変わり得る |
| 本人/役視点 | 本人を選び、情報で条件付けたTable確率と能力先別値。狼は各行への襲撃、占いは各行への占い。本人選択は能力先確定ではない。狩人は未対応 | Tableは既にA。公開全体側もAへ移し、モデルと期限内値の参照を揃える |
| 右端襲撃フラグ | /dawn-reportが今夜の死体指定を保存しrevisionを更新。進行できる観測か検査するが、現在Boardの確率/勝率へ適用しない。役視点中は編集無効 | この操作意味は変更しない。フラグにより仮想対象行やOverviewを条件付けない |
| BoardOverview | 公開情報の現在/累積勝率。本人視点への切替で差し替えない | 公開モデルをAへ変えるため値は変わり得る。本人の私的値へOverviewも差し替える表示変更はまだ実装していない |
| 翌昼へ進む | /dawn-advanceが死体観測をhistoryへ追加し、observe/advance_stepで初めて死亡・条件付け・phase更新。秘密欄を公開しない | 進行契約は維持。到達後の計算を統合facadeへ揃える |

根拠：app.render_mainはreplayした現在progress.boardを使う。render_dawnで仮にobserveしたafterは進行可否/終局チェックに使い、数値のBoardとしてrender_mainへ渡さない。dawn_reportはrecord_observationだけ、dawn_advanceでhistoryへ追記する。static/app.js:initializeStatusChoicesはフラグを/dawn-reportへ送る。templates/board_table.htmlは選択の有無に関係なくplayer.action/player.by_dawnを各行へ描画する。

static/board_private_table.js:showはTableのdata-value-cellだけを更新し、rate-cardやOverviewの狼数分布を更新しない。app.private_viewはrole/players/resultsを受け取り、現在公開Boardから私的計算する。例えば占い師P3本人を選ぶことと、P3行を占い先として評価することは別で、本人は自己占いの対象にならない。

「Overlay」がどの領域を指すかは断定しない。現行の戦略dialogはStrategy Item編集で、strategy_seedに勝率値は渡していない。BoardOverviewなら上記の公開カードであり、視点選択やフラグで既に勝率を変更していたという事実はない。公開CO/結果や戦略そのものを変更して適用した場合の再計算は別。

## 前の質問の訂正と残る数値契約

既存UIの「この行の対象を襲撃した場合」を維持するなら、「設定戦略が自然にその対象を選ぶイベント」の勝率へ変える表示選択を聞く必要はない。フラグの有無も、この行の比較条件とは無関係だった。

残るのは、全体priorにP3が狼仲間となる配役も混ざるとき、実行不可能な配役を除いた条件付き分布をどう定めるかという数値契約。旧指定行動は狼数ごとに正規化して事前狼数分布を保つ。Aの仲間別選択/物理分布へ移す際の条件付けはそれと同じではない。Overviewの旧7/8とA5/6などもモデル差で、フラグ操作による差ではない。

合法配役に条件付けた対象指定比較が既存の表示意味に沿う推奨案。ただし今回のユーザー反応だけでその条件付けの承認とはせず、全体夜行の切替はまだ保留する。新しい操作や表示選択を増やす話にはしない。

## 追加回帰

test_night_flag_scopeで、5人の現在夜Boardについてフラグ前後の全体の全data-fractionと狼視点のplayers値が完全一致し、replayした現在Boardも同一であることを確認。翌昼へ進んだ後に初めて指定対象がaliveから消え、day/phaseとBoardが更新される。追加1テスト成功（0.196秒）。
