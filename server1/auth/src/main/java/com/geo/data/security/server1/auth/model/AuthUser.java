package com.geo.data.security.server1.auth.model;

import java.util.Set;

public record AuthUser(
        String userId,
        String username,
        String password,
        String displayName,
        String role,
        Set<String> permissions,
        boolean enabled
) {
}
