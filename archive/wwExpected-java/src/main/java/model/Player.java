package model;

import java.util.LinkedHashMap;
import java.util.Map;

import model.role.child.Latent;
import model.role.person.Role;

public class Player {
	String mainDisplay = "";

	int id;
	String name;
	Role co;
	boolean alive = true;

	Role confRole;

	Map<Role, Float> truePerMap = new LinkedHashMap<>();
	Map<Role, Float> villsTruePerMap = new LinkedHashMap<>();
	Map<Role, Float> wwsTruePerMap = new LinkedHashMap<>();

	Map<Role, FaseBoard> parallelFbMap = new LinkedHashMap<>();
	float villsPer;
	float wwsPer;
	float wPer;
	float kPer;

	float exedVillsWinPer;
	float exedWwsWinPer;
	String outExedPer;

	public Player(int i, Latent latent, Map<Role, Integer> roleSizeMap) {
		id = i + 1;
		this.name = "player" + this.id;
		co = latent;
		for (Role role : roleSizeMap.keySet()) {
			switch (role.getCamp()) {
			case "村s":
				villsTruePerMap.put(role, 0f);
				break;
			case "狼s":
				wwsTruePerMap.put(role, 0f);
				break;
			}
		}
	}

	public Player(int num, String name, Role co, boolean alive) {
		this.id = num;
		this.name = name;
		this.co = co;
		this.alive = alive;
	}

	public String getMainDisplay() {
		return mainDisplay;
	}

	public void setMainDisplay(String mainDisplay) {
		this.mainDisplay = mainDisplay;
	}

	public int getId() {
		return id;
	}

	public void setId(int num) {
		this.id = num;
	}

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public Role getCo() {
		return co;
	}

	public void setCo(Role co) {
		this.co = co;
	}

	public boolean isAlive() {
		return alive;
	}

	public void setAlive(boolean alive) {
		this.alive = alive;
	}

	public Role getConfRole() {
		return confRole;
	}

	public void setConfRole(Role confRole) {
		this.confRole = confRole;
		this.co = confRole;
		this.truePerMap.put(confRole, 1.0f);
		this.truePerMap.replaceAll((key, value) -> key.equals(confRole) ? value : 0);
		
	}

	public float getVillsPer() {
		return villsPer;
	}

	public void setVillsPer(float villsPer) {
		this.villsPer = villsPer;
	}

	public Map<Role, Float> getTruePerMap() {
		return truePerMap;
	}

	public void setTruePerMap(Map<Role, Float> truePerMap) {
		this.truePerMap = truePerMap;
	}

	public Map<Role, Float> getVillsTruePerMap() {
		return villsTruePerMap;
	}

	public void setVillsTruePerMap(Map<Role, Float> villsTruePerMap) {
		this.villsTruePerMap = villsTruePerMap;
	}

	public Map<Role, Float> getWwsTruePerMap() {
		return wwsTruePerMap;
	}

	public void setWwsTruePerMap(Map<Role, Float> wwsTruePerMap) {
		this.wwsTruePerMap = wwsTruePerMap;
	}

	public Map<Role, FaseBoard> getParallelFbMap() {
		return parallelFbMap;
	}

	public void setParallelFbMap(Map<Role, FaseBoard> parallelFbMap) {
		this.parallelFbMap = parallelFbMap;
	}

	public float getWwsPer() {
		return wwsPer;
	}

	public void setWwsPer(float wwsPer) {
		this.wwsPer = wwsPer;
	}

	public float getwPer() {
		return wPer;
	}

	public void setwPer(float wPer) {
		this.wPer = wPer;
	}

	public float getkPer() {
		return kPer;
	}

	public void setkPer(float kPer) {
		this.kPer = kPer;
	}

	public float getExedVillsWinPer() {
		return exedVillsWinPer;
	}

	public void setExedVillsWinPer(float exedVillsWinPer) {
		this.exedVillsWinPer = exedVillsWinPer;
	}

	public float getExedWwsWinPer() {
		return exedWwsWinPer;
	}

	public void setExedWwsWinPer(float exedWwsPer) {
		this.exedWwsWinPer = exedWwsPer;
	}

	public String getOutExedPer() {
		return outExedPer;
	}

	public void setOutExedPer(String outExedPer) {
		this.outExedPer = outExedPer;
	}
	
	

}