<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ taglib prefix="c" uri="jakarta.tags.core"%>

<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>main</title>
<style>
table {
	border-collapse: collapse; /* セル間のボーダーを統合 */
	width: 70%; /* テーブルの幅を100%に設定 */
}

th, td {
	border: 1px solid black; /* 各セルに1pxのボーダーを設定 */
	padding: 1px; /* セル内に少し余白を設定 */
	text-align: center; /* セル内の文字を中央揃え */
}
</style>

</head>
<body>
	${sr.outRegulation}
	<br> ${d1.winner}
	<form action="top" method="post">
		<table>
			<tr>
				<th>exe</th>
				<th>id</th>
				<th>name</th>
				<th>co</th>
				<th>村s%▶</th>
				<c:forEach var="role" items="${sr.villsRoleSizeMap.keySet()}">
					<th>${role}%</th>
				</c:forEach>
				<th>狼s%▶</th>
				<c:forEach var="role" items="${sr.wwsRoleSizeMap.keySet()}">
					<th>${role}%</th>
				</c:forEach>
				<th>win%</th>
			</tr>

			<c:forEach var="i" begin="0" end="${sr.roleList.size()-1}" step="1">
				<tr>
					<td><input type="radio" name="exe" value="${i}"></td>
					<td>${i+1}</td>
					<td><input type="text" name="${i}_name" style="width: 60px"></td>
					<td><select name="${i}_co" style="width: 60px">
							<option value="null">?</option>
							<c:forEach var="canCo" items="${sr.canCoList}">
								<option value="${canCo}">${canCo}</option>
							</c:forEach>
					</select></td>
					<td>${tj.perF(d1.playerList.get(i).villsPer)}</td>
					<c:forEach var="role" items="${d1.playerList.get(i).villsTruePerMap.keySet()}">
						<td>${tj.perF(d1.playerList.get(i).villsTruePerMap.get(role))}</td>
					</c:forEach>
					<td>${tj.perF(d1.playerList.get(i).wwsPer)}</td>
					<c:forEach var="role" items="${d1.playerList.get(i).wwsTruePerMap.keySet()}">
						<td>${tj.perF(d1.playerList.get(i).wwsTruePerMap.get(role))}</td>
					</c:forEach>
					<td>${tj.perF(d1.playerList.get(i).exedVillsWinPer)}/${tj.perF(d1.playerList.get(i).exedWwsWinPer)}</td>
				</tr>
			</c:forEach>
		</table>
	</form>
	<div>
		<a href="http://localhost:8080/wwExpected/top" style="text-decoration: none;"><button style="margin-right: 100px;">TOPに戻る</button></a>
		<button style="margin-right: 2px;">初日に戻る</button>
		<button style="margin-right: 2px;">1日戻る</button>
		<button style="margin-right: 30px;">戻る</button>
		<button style="margin-right: 2px;">実行</button>
		<button type="submit" name="action" value="updeate">更新</button>
	</div>


</body>
</html>