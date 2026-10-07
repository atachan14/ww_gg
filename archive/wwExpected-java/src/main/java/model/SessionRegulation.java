package model;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import jakarta.servlet.http.HttpServletRequest;

import model.role.child.Latent;
import model.role.person.Role;

public class SessionRegulation implements Serializable {
	private List<Role> roleList = new ArrayList<>();
	private List<Role> villsList = new ArrayList<>();
	private List<Role> wwsList = new ArrayList<>();
	//(市民,市民,市民,狼,狼...)

	private List<Role> canCoList = new ArrayList<>();
	private Map<Role, Integer> roleSizeMap = new LinkedHashMap<>();
	private Map<Role, Integer> villsRoleSizeMap = new LinkedHashMap<>();
	private Map<Role, Integer> wwsRoleSizeMap = new LinkedHashMap<>();
	//(市民3,狼2...)

	private String outRegulation = "";
	private String outVills = "";
	private String outWWs = "";

	public SessionRegulation(HttpServletRequest request) {
		FaseBoard.setSr(this);
		Cog.setSr(this);

		criateRoles(request);
		criateCamps();
	}

	public SessionRegulation() {

	}

	void criateRoles(HttpServletRequest request) {
		for (Map.Entry<String, String[]> entry : request.getParameterMap().entrySet()) {
			String key = entry.getKey();
			String value = entry.getValue()[0];
			if (value == null || value.isEmpty() || value.equals("0")) {
				continue; // 空文字、null、または"0"をスキップ
			}
			System.out.println(entry.getKey() + ":" + value);

			Role role = RoleFactory.createRole(key);
			int size = Integer.parseInt(entry.getValue()[0]);

			roleSizeMap.put(role, size);
			canCoList.add(role);

			for (int i = 0; i < size; i++) {
				roleList.add(role);
			}
		}
		Latent latent = new Latent();
		canCoList.add(latent);

		// debug用
		System.out.print("list:");
		for (Role role : roleList) {
			System.out.print("[" + role.getName() + "]");
		}
		System.out.println();

		System.out.print("map:");
		for (Map.Entry<Role, Integer> entry : roleSizeMap.entrySet()) {
			System.out.print("[" + entry.getKey().getName() + "*" + entry.getValue() + "]");
		}
		System.out.println();
		System.out.println();
	}

	void criateCamps() {
		for (Role role : roleList) {
			switch (role.getCamp()) {
			case "村s":
				villsList.add(role);
				break;
			case "狼s":
				wwsList.add(role);
				break;
			default:
				System.out.println("sr.criateCamps1");
				break;
			}
		}

		outVills = "【村陣営:" + villsList.size() + "人】";
		outWWs = "【狼陣営:" + wwsList.size() + "人】";

		for (Map.Entry<Role, Integer> entry : roleSizeMap.entrySet()) {
			switch (entry.getKey().getCamp()) {
			case "村s":
				villsRoleSizeMap.put(entry.getKey(), entry.getValue());
				outVills += "[" + entry.getKey().getName() + entry.getValue() + "]";
				break;
			case "狼s":
				wwsRoleSizeMap.put(entry.getKey(), entry.getValue());
				outWWs += "[" + entry.getKey().getName() + entry.getValue() + "]";
				break;
			default:
				System.out.println("sr.criateCamps2");
				break;
			}
		}
		outRegulation = outVills + " " + outWWs;
	}

	public List<Role> getRoleList() {
		return roleList;
	}

	public List<Role> getVillsList() {
		return villsList;
	}

	public List<Role> getWwsList() {
		return wwsList;
	}

	public Map<Role, Integer> getRoleSizeMap() {
		return roleSizeMap;
	}

	public Map<Role, Integer> getVillsRoleSizeMap() {
		return villsRoleSizeMap;
	}

	public Map<Role, Integer> getWwsRoleSizeMap() {
		return wwsRoleSizeMap;
	}

	public List<Role> getCanCoList() {
		return canCoList;
	}

	public String getOutRegulation() {
		return outRegulation;
	}

	public String getOutVills() {
		return outVills;
	}

	public String getOutWWs() {
		return outWWs;
	}

}
