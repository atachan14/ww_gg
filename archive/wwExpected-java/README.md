# wwExpected Java参考スナップショット

初期の人狼期待勝率計算プロジェクトを、再設計時の参考資料として保存したものです。完成済みの計算器や正解値の基準として扱うものではありません。

## 出典と保存方法

- 元フォルダ: `G:\source\repos\動的web\wwExpected`
- 保存先: `G:\source\repos\Python\ww_gg\archive\wwExpected-java`
- 取得日時（UTC）: `2026-10-06T23:16:28+00:00`
- 元フォルダの現内容から35ファイルを複製しました。Gitのコミット状態に関係なく、選定ファイルの現内容（未コミット変更を含み得る）を保存しています。Git操作や状態調査はしていません。
- 元ファイルは変更していません。既存の保存先を上書きする処理はありません。
- 調査時、元のルートにREADMEやdocsは見当たりませんでした。コメント内のメモはソースと一緒に保存しています。
- このREADMEと `SOURCE-SHA256.json` の2ファイルを、保存記録として新規作成しました。元ファイル由来の35件と合わせて計37ファイルです。

## 参考になる意図

- `FaseBoard.java`: 各候補プレイヤーについて役職別の次盤面を再帰生成し、子盤面の勝率を分岐確率で重み付けする構想。
- `Cog.java` / `Latentg.java`: CO別のグループと潜伏者グループを使って役職確率を整理する構想。
- `Player.java`: 役職確率と「この人を処刑した場合の勝率」を別の値として保持する構想。
- `main.jsp` / `top.jsp`: 編成人数の入力から、プレイヤーごとのCO・役職確率・行動後の勝率を並べる画面へ進む構想。
- `debug/Memo.java`: 当時の未解決事項の記録。

入力→候補行動→確率分岐→将来の勝敗→期待勝率、という目的の資料です。将来の行動選択、夜の合法行動、情報の扱い、終端判定などは完成が確認されていません。旧実装の再利用可否は、この意図の保存とは別に判断してください。Javaの実行・ビルド・テスト・依存インストールは行っていません。

## 保存対象と除外方針

保存対象はJavaソース22件、JSP/CSS/MANIFESTの4件、Eclipseのプロジェクト・コンパイラ・Web設定9件です。元設定にはJava 21、Tomcat 10、Web facet 6.0が記録されています。依存物を同梱しないため、そのまま動く配布物ではありません。

除外したもの:

- `.git/`: 履歴・Git内部情報。
- `build/`: 生成物。
- `src/main/webapp/WEB-INF/lib/`: 外部依存バイナリ。名前だけを記録し、内容を読み取ったり複製したりしていません。
  - `h2-2.3.232.jar`
  - `jakarta.servlet.jsp.jstl-3.0.1.jar`
  - `jakarta.servlet.jsp.jstl-api-3.0.0.jar`
- 依存キャッシュ、秘密情報、資格情報、個人データは対象外です。指定したファイルの許可リストだけをコピーしています。

元Python版の移動・入替えや、別プロジェクト `gg_ww2` の変更は行っていません。

## コピー一覧

SHA-256は `SOURCE-SHA256.json` に各ファイルのサイズと共に記録しました。コピー後に元・保存先の全35件を照合しています。

| 元からの相対パス | バイト数 |
| --- | ---: |
| `.classpath` | 738 |
| `.project` | 910 |
| `.settings/.jsdtscope` | 572 |
| `.settings/org.eclipse.core.resources.prefs` | 57 |
| `.settings/org.eclipse.jdt.core.prefs` | 547 |
| `.settings/org.eclipse.wst.common.component` | 581 |
| `.settings/org.eclipse.wst.common.project.facet.core.xml` | 343 |
| `.settings/org.eclipse.wst.jsdt.ui.superType.container` | 49 |
| `.settings/org.eclipse.wst.jsdt.ui.superType.name` | 6 |
| `src/main/java/debug/Memo.java` | 457 |
| `src/main/java/listener/SetupApllication.java` | 1093 |
| `src/main/java/model/Cog.java` | 4151 |
| `src/main/java/model/Fase.java` | 523 |
| `src/main/java/model/FaseBoard.java` | 6189 |
| `src/main/java/model/Latentg.java` | 1446 |
| `src/main/java/model/Player.java` | 3756 |
| `src/main/java/model/RoleFactory.java` | 1174 |
| `src/main/java/model/SessionRegulation.java` | 3831 |
| `src/main/java/model/logic/ToJSP.java` | 246 |
| `src/main/java/model/role/child/Hunter.java` | 169 |
| `src/main/java/model/role/child/Latent.java` | 171 |
| `src/main/java/model/role/child/Madman.java` | 165 |
| `src/main/java/model/role/child/Medium.java` | 169 |
| `src/main/java/model/role/child/Prophet.java` | 171 |
| `src/main/java/model/role/child/Villager.java` | 171 |
| `src/main/java/model/role/child/Wolf.java` | 156 |
| `src/main/java/model/role/person/Role.java` | 442 |
| `src/main/java/model/role/person/Vills.java` | 141 |
| `src/main/java/model/role/person/WWs.java` | 135 |
| `src/main/java/servlet/MainServlet.java` | 1497 |
| `src/main/java/servlet/TopServlet.java` | 1703 |
| `src/main/webapp/css/styles.css` | 458 |
| `src/main/webapp/META-INF/MANIFEST.MF` | 39 |
| `src/main/webapp/WEB-INF/jsp/main.jsp` | 2653 |
| `src/main/webapp/WEB-INF/jsp/top.jsp` | 509 |
