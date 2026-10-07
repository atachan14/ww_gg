package model;

import java.util.Map.Entry;

import model.role.person.Role;

public class Latentg extends Cog {
	public Latentg(FaseBoard sb, Role latent) {
		super(sb, latent);
	}

	@Override
	void countSizes() {
		size = this.playerList.size();
		trueSize = fb.getVillsVacantSizeMap().values().stream()
				.reduce(0, (a, b) -> a + b);
		falseSize = size - trueSize;

		if (size == 0)
			return;

		truePer = (float) trueSize / size;
		falsePer = (float) falseSize/ size;

	}

	@Override
	void updateTruePer() {
		if (!isFull) {
			return;
			//あとで実装
			//truePer=100%?
		}

		float eachTruePer = truePer / trueSize;
		float eachFalsePer = falsePer / falseSize;

		for (Player player : playerList) {
			player.setVillsPer((float) Math.ceil(truePer * 10000) / 10000);
			player.setWwsPer((float) Math.ceil((1 - truePer) * 10000) / 10000);

			
			for (Entry<Role,Integer> entry : fb.getVillsVacantSizeMap().entrySet()) {
				float temp = (float) entry.getValue() * eachTruePer;
				player.getVillsTruePerMap().put(entry.getKey(),temp);
			}
			
			for (Entry<Role,Integer> entry : fb.getWwsVacantSizeMap().entrySet()) {
				float temp = (float) entry.getValue() * eachFalsePer;
				player.getWwsTruePerMap().put(entry.getKey(),temp);
			}
			
			player.getTruePerMap().putAll(player.getVillsTruePerMap());
			player.getTruePerMap().putAll(player.getWwsTruePerMap());

		}
	}
}
