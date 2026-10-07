package model;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import model.role.person.Role;

public class Cog {
	static SessionRegulation sr;
	FaseBoard fb;
	Role co;
	List<Player> playerList;

	int size = 0;
	int trueSize = 0;

	int falseSize = 0;
	int confSize = 0;
	int vacant = 0;

	Map<Role, Integer> campVacantSizeMapIB;
	boolean isFull = false;

	float truePer;
	float falsePer;

	int confAliveVills;
	int confAliveEvils;
	int confDeadVills;
	int confDeadEvils;

	public Cog(FaseBoard sb, Role role) {
		this.fb = sb;
		this.co = role;
		//		System.out.println(role.getName() + "groupのプレイヤーサイズ:" + playerList.size());
		criatePlayerList();
		campSetup();
		countSizes();
		checkIsFull();
		updateTruePer();
		countConfWws();

	}

	void criatePlayerList() {
		playerList = fb.getPlayerList().stream()
				.filter(a -> a.getCo() == co)
				.collect(Collectors.toList());
	}

	void campSetup() {
		switch (this.co.getCamp()) {
		case "村s":
			campVacantSizeMapIB = fb.getVillsVacantSizeMap();
			break;

		case "狼s":
			campVacantSizeMapIB = fb.getWwsVacantSizeMap();
			break;

		default:
			System.out.println("Cog.selectMapAndListIB() this.co.getCamp():" + this.co.getCamp());
			break;
		}
	}

	void countSizes() {
		size = this.playerList.size();
		trueSize = sr.getRoleSizeMap().get(this.co);
		falseSize = size - trueSize;

		confSize = (int) this.playerList.stream()
				.filter(a -> a.getConfRole() == this.co)
				.count();
		vacant = trueSize - size;
		campVacantSizeMapIB.put(this.co, vacant);

		if (size == 0)
			return;

		truePer = (float) trueSize / size;
		falsePer = (float) 1 - truePer;

		if (vacant <= 0) {
			isFull = true;
		} else {
			isFull = false;
		}
	}

	void checkIsFull() {
		if (trueSize <= size) {
			isFull = true;
			return;
		}
		isFull = false;
	}

	void updateTruePer() {
		if (!isFull) {
			return;
			//あとで実装
			//replaceAllで他を0にしてlatentListと一緒にVillsPerを算出してtruePerに入れる？
		}

		for (Player player : playerList) {
			player.setVillsPer((float) Math.ceil(truePer * 10000) / 10000);
			player.setWwsPer((float) Math.ceil(falsePer * 10000) / 10000);

			switch (this.co.getCamp()) {
			case "村s":
				player.getVillsTruePerMap().put(this.co, truePer);
				player.getVillsTruePerMap().replaceAll((key, value) -> key.equals(this.co) ? value : 0);
				break;
			case "狼s":
				System.out.println("cog.updateTruePer switch:狼s");
				break;

			default:
				System.out.println("cog.updateTruePer switch:default");
			}
			player.getTruePerMap().putAll(player.getVillsTruePerMap());
			player.getTruePerMap().putAll(player.getWwsTruePerMap());
		}

	}

	public void countConfWws() {

		float temp = playerList.stream()
				.filter(p -> p.isAlive())
				.map(p -> p.getVillsPer())
				.reduce(0.0f, (a, b) -> a + b);
		confAliveVills = (int) Math.floor(temp);

		temp = playerList.stream()
				.filter(p -> p.isAlive())
				.map(p -> p.getWwsPer())
				.reduce(0.0f, (a, b) -> a + b);
		confAliveEvils = (int) Math.floor(temp);

		temp = playerList.stream()
				.filter(p -> !p.isAlive())
				.map(p -> p.getWwsPer())
				.reduce(0.0f, (a, b) -> a + b);
		confDeadEvils = (int) Math.floor(temp);

		//		↓ok!
		//		System.out.println(co+"g.confDeadWws:"+confDeadWws);
		//		System.out.println(co+"g.confAliveWws:"+confAliveWws);
	}

	public int size() {
		return playerList.size();
	}

	public int getVacant() {
		return vacant;
	}

	public List<Player> getList() {
		return playerList;
	}

	public boolean getIsFull() {
		return isFull;
	}

	public int getTrueSize() {
		return trueSize;
	}

	public int getConfAliveVills() {
		return confAliveVills;
	}

	public int getConfAliveEvils() {
		return confAliveEvils;
	}

	public int getConfDeadVills() {
		return confDeadVills;
	}

	public int getConfDeadEvils() {
		return confDeadEvils;
	}

	public static void setSr(SessionRegulation SR) {
		sr = SR;
	}
}
