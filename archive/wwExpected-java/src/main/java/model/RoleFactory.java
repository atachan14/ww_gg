package model;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.Supplier;

import model.role.child.Hunter;
import model.role.child.Madman;
import model.role.child.Medium;
import model.role.child.Prophet;
import model.role.child.Villager;
import model.role.child.Wolf;
import model.role.person.Role;

public class RoleFactory {
    private static final Map<String, Supplier<Role>> appRoleMap = new LinkedHashMap<>();

    static {
        appRoleMap.put("市民", Villager::new);
        appRoleMap.put("占師", Prophet::new);
        appRoleMap.put("霊能", Medium::new);
        appRoleMap.put("狩人", Hunter::new);
        appRoleMap.put("狂人", Madman::new);
        
        appRoleMap.put("狼", Wolf::new);
    }

    public static Role createRole(String roleName) {
        Supplier<Role> roleSupplier = appRoleMap.get(roleName);
        if (roleSupplier == null) {
            throw new IllegalArgumentException("Unknown role: " + roleName);
        }
        return roleSupplier.get();
    }

	public static Map<String, Supplier<Role>> getAppRoleMap() {
		return appRoleMap;
	}
    
}

