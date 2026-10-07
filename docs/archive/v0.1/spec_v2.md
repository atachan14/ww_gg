
# 立場ごとのムーブ（COタイミング等）も全部枝にする案
## 昼phaseを細分化
1. 朝phase
	1. actionチェック
2. 処刑対象指定phase
	1. 処刑対象を指定する
	2. actionチェック
3. 処刑対象決定phase
	1. 処刑対象決定
		1. actionチェック（決定後は指定後と違い、対象の再選択を行わない）

## [actionチェック]
立場ごと（村戦略：[COは取り消せない]前提）に COする/しない や 能力結果の開示 等の分岐を行うPhase。

    例（白を貰ってる等でplayer1のみが違う立場のケース）
    1. player1
        1. player1が真占だった場合のCO分岐
        2. player1が真霊だった場合のCO分岐
        3. player1が真狩だった場合のCO分岐
        4. player1が真市民だった場合のCO分岐
        5. player1が真狂だった場合のCO分岐
        6. player1が真狼だった場合のCO分岐
    2. player2,3,4グループ
        1. player2,3,4グループに真占がいた場合のCO分岐
        2. player2.3.4グループに真霊がいた場合のCO分岐
        3. ...

actionが行われるたびに、そのphaseを追加で行う。

    例1:
    朝phase1[player1がCO]
    → 朝phase2[player2がカウンターCO]
    → 朝phase3[player1が能力結果開示]
    → 朝phase4[誰もactionしない]
    → 次のphaseへ進む。

    例2:
    処刑対象指定phase1[player1を処刑対象に指定][player1がCO]
    → phase2[player2を処刑対象に指定][player2がCO]
    → phase3[player1を処刑対象に指定][誰もactionしない]
    → 次のphaseに進む

# ユーザー入力をどこまで残すか。
全て残して、入力によってNodeを移動する。
例えば、Player1のCOを「潜伏」から「占い」に変えた場合、
Player1が「占い」をCOしているNodeに移動する。