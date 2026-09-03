package com.geo.data.security.server1.auth.model;

public record LoginResult(
        String token,
        String tokenType,
        long expiresInSeconds,
        AuthPrincipal principal
) {
}
