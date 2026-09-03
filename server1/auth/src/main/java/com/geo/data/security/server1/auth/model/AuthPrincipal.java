package com.geo.data.security.server1.auth.model;

import java.time.Instant;
import java.util.Set;

public record AuthPrincipal(
        String userId,
        String username,
        String displayName,
        String role,
        Set<String> permissions,
        String tokenId
) {
}
