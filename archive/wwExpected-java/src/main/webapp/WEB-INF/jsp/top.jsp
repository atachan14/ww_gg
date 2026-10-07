<%@ page language="java" contentType="text/html; charset=UTF-8"
	pageEncoding="UTF-8"%>
<%@ taglib prefix="c" uri="jakarta.tags.core"%>

<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>top</title>
</head>
<body>
	<form action="top" method="post">
		<input type="submit" value="go"><br>
		<c:forEach var="key" items="${appRoleMap.keySet()}">
			<c:out value="${key}" />:
			<input type="number" name="${key}" style="width: 30px;">
			<br>
		</c:forEach>
	</form>
</body>
</html>