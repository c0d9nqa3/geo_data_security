package com.geo.data.security.server1.common.context;

import java.util.Set;

public record AccessPrincipal(
        String userId,
        String username,
        String displayName,
        String role,
        Set<String> permissions
) {
    public AccessPrincipal(String userId, String username, String displayName, String role) {
        this(userId, username, displayName, role, Set.of());
    }

    public AccessPrincipal {
        permissions = permissions == null ? Set.of() : Set.copyOf(permissions);
    }

    public boolean hasPermission(String permCode) {
        return permCode != null && permissions.contains(permCode);
    }
}
