package model.role.person;

public class Role {
	String name = "person";
	String camp = "person";

	@Override
	public String toString() {
		return name;
	}

	public void nightAction() {

	}

	public String getName() {
		return this.name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public String getCamp() {
		return camp;
	}

	public void setCamp(String camp) {
		this.camp = camp;
	}

}
