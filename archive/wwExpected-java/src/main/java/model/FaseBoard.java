package model;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import model.role.child.Latent;
import model.role.person.Role;

public class FaseBoard implements Serializable {
	static SessionRegulation sr;
	Fase fase;

	String winner = "--";
	//	boolean villsWin = false;
	//	boolean wwsWin = false;
	//	boolean draw = false;
	float villsWinPer;
	float evilsWinPer;

	float boardPer;

	List<Player> playerList = new ArrayList<>();

	Map<Role, Cog> cogMap = new LinkedHashMap<>();
	List<Cog> cogList = new ArrayList<>();

	Map<Role, Integer> villsVacantSizeMap = new LinkedHashMap<>();
	int latentEvilsSize = 0;
	Map<Role, Integer> wwsVacantSizeMap = new LinkedHashMap<>();

	List<Player> alivePlayerList;
	int confAliveVillsIB = 0;
	int confAliveEvilsIB = 0;

	Fase nextFase;
	Player exedPlayer;

	public FaseBoard() {

	}

	public FaseBoard(Fase fase) {
		this.fase = fase;
		this.boardPer = 1.0f;
		criatePlayerList();

		setup();
		
		toToJSP();

	}

	//	nextFase, boardPer,p.getNum(),role, this
	public FaseBoard(Fase fase, float boardPer, int num, Role role, FaseBoard beforBoard) {
		this.fase = fase;
		this.boardPer = boardPer;
		System.out.println("boardPer:" + boardPer);
		criateCopyedPlayerList(beforBoard);
		exeExedPlayer(num, role);

		setup();
	}

	void setup() {
		criateAlivePlayerList();
		System.out.println("alivePlayerList.size()" + alivePlayerList.size());
		criateCogMap();

		countConfAlives();
		checkEnd();

		if (winner == "--") {
			System.out.println("	if (winner == \"--\") {");
			criateNextFase();
			criateParallelFbMap();
			calcExedWinPer();
			System.out.println("	}");
		}
	}

	void criatePlayerList() {
		Latent latent = (Latent) sr.getCanCoList().stream()
				.filter(a -> a.getName() == "？")
				.findAny()
				.get();
		for (int i = 0; i < sr.getRoleList().size(); i++) {
			playerList.add(new Player(i, latent, sr.getRoleSizeMap()));
		}

		latentEvilsSize = sr.getWwsList().size();
	}

	void criateCopyedPlayerList(FaseBoard beforBoard) {
		playerList = beforBoard.getPlayerList().stream()
				.map(p -> new Player(p.getId(), p.getName(), p.getCo(), p.isAlive()))
				.collect(Collectors.toList());
	}

	void exeExedPlayer(int num, Role role) {
		this.exedPlayer = playerList.get(num - 1);
		exedPlayer.setAlive(false);
		exedPlayer.setConfRole(role);
	}

	void criateAlivePlayerList() {
		alivePlayerList = playerList.stream()
				.filter(p -> p.isAlive())
				.collect(Collectors.toList());
	}

	void criateCogMap() {
		for (Role co : sr.getCanCoList()) {
			if (co.getName() == "？") {
				Latentg latentg = new Latentg(this, co);
				cogMap.put(co, latentg);
			} else {
				Cog cog = new Cog(this, co);
				cogMap.put(co, cog);
			}

		}
	}

	void countConfAlives() {
		confAliveVillsIB = cogMap.values().stream()
				.mapToInt(Cog::getConfAliveVills)
				.sum();

		confAliveEvilsIB = cogMap.values().stream()
				.mapToInt(Cog::getConfAliveEvils)
				.sum();
	}

	void checkEnd() {
		System.out.println("confAliveVillsIB:" + confAliveVillsIB + " confAliveEvilsIB:" + confAliveEvilsIB);

		if (confAliveVillsIB >= 1 && confAliveEvilsIB == 0) {
			villsWinPer = 1.0f;
			evilsWinPer = 0f;
			winner = "村WIN";
		} else if (confAliveVillsIB == confAliveEvilsIB && confAliveEvilsIB > 0) {
			villsWinPer = 0f;
			evilsWinPer = 1.0f;
			winner = "人狼WIN";
		} else if (confAliveVillsIB == confAliveEvilsIB && confAliveEvilsIB == 0) {
			villsWinPer = 0.5f;
			evilsWinPer = 0.5f;
			winner = "DRAW";
		} else {
			System.out.println("checkEnd next");
		}
		System.out.println(winner);
	}

	void criateNextFase() {
		switch (this.fase.getZone()) {
		case "d":
			nextFase = new Fase("n", fase.getDay());
			break;

		case "n":
			nextFase = new Fase("d", fase.getDay() + 1);
			break;
		default:
			nextFase = new Fase("?", 0);
			System.out.println("nextFase error→" + this.fase);
			break;
		}
	}

	void criateParallelFbMap() {
		for (Player p : alivePlayerList) {
			for (Role role : p.getTruePerMap().keySet()) {
				float nextBoardPer = p.getTruePerMap().get(role);
				FaseBoard nextFb = new FaseBoard(nextFase, nextBoardPer, p.getId(), role, this);
				p.getParallelFbMap().put(role, nextFb);

			}
			System.out.println("criateParallelFbMap p.id:" + p.getId() + "+p.getTruePerMap().size:"
					+ p.getTruePerMap().size() + " ,getParallelFbMap.size:" + p.getParallelFbMap().size());
		}
	}

	void calcExedWinPer() {
		for (Player player : playerList) {
			float winPer = 0;
			for (Role role : player.getParallelFbMap().keySet()) {
				winPer += player.getParallelFbMap().get(role).getVillsWinPer()
						* player.getParallelFbMap().get(role).getBoardPer();
			}
			player.setExedVillsWinPer(winPer);
			player.setExedWwsWinPer(1 - winPer);
			player.setOutExedPer(winPer + "/" + (1 - winPer));
		}
	}
	
	void toToJSP() {
		
	}

	public List<Player> getPlayerList() {
		return playerList;
	}

	public Map<Role, Cog> getCogMap() {
		return cogMap;
	}

	public List<Cog> getCogList() {
		return cogList;
	}

	public Map<Role, Integer> getVillsVacantSizeMap() {
		return villsVacantSizeMap;
	}

	public int getLatentEvilsSize() {
		return latentEvilsSize;
	}

	public Map<Role, Integer> getWwsVacantSizeMap() {
		return wwsVacantSizeMap;
	}

	public String getWinner() {
		return winner;
	}

	public Fase getFase() {
		return fase;
	}

	public float getBoardPer() {
		return boardPer;
	}

	public List<Player> getAlivePlayerList() {
		return alivePlayerList;
	}

	public int getConfAliveVillsIB() {
		return confAliveVillsIB;
	}

	public int getConfAliveEvilsIB() {
		return confAliveEvilsIB;
	}

	public Player getExedPlayer() {
		return exedPlayer;
	}

	public float getVillsWinPer() {
		return villsWinPer;
	}

	public float getWwsWinPer() {
		return evilsWinPer;
	}

	public static void setSr(SessionRegulation SR) {
		sr = SR;
	}

}
