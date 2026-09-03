package com.geo.data.security.server1.auth.service;

import com.geo.data.security.server1.auth.config.AuthProperties;
import com.geo.data.security.server1.auth.error.AuthException;
import com.geo.data.security.server1.auth.model.AuthPrincipal;
import com.geo.data.security.server1.auth.model.AuthUser;
import com.geo.data.security.server1.auth.model.TokenSession;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Arrays;
import java.util.Date;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class JwtTokenService {

    private final AuthProperties properties;

    public JwtTokenService(AuthProperties properties) {
        this.properties = properties;
    }

    public String issue(AuthUser user, String tokenId, Instant issuedAt, Instant expiresAt) {
        return Jwts.builder()
                .id(tokenId)
                .subject(user.userId())
                .claim("username", user.username())
                .claim("displayName", user.displayName())
                .claim("role", user.role())
                .claim("permissions", String.join(",", user.permissions()))
                .issuedAt(Date.from(issuedAt))
                .expiration(Date.from(expiresAt))
                .signWith(secretKey())
                .compact();
    }

    public AuthPrincipal parseAndBuildPrincipal(String token) {
        Claims claims = parseClaims(token);
        String permissions = stringClaim(claims, "permissions");
        Set<String> permissionSet = permissions.isBlank()
                ? Set.of()
                : Arrays.stream(permissions.split(",")).filter(s -> !s.isBlank()).collect(Collectors.toSet());
        return new AuthPrincipal(
                claims.getSubject(),
                stringClaim(claims, "username"),
                stringClaim(claims, "displayName"),
                stringClaim(claims, "role"),
                permissionSet,
                claims.getId() == null ? "" : claims.getId()
        );
    }

    public Claims parseClaims(String token) {
        try {
            return Jwts.parser()
                    .verifyWith(secretKey())
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
        } catch (Exception ex) {
            throw new AuthException("AUTH-401", "令牌无效或已过期");
        }
    }

    public String newTokenId() {
        return UUID.randomUUID().toString().replace("-", "");
    }

    public TokenSession toSession(AuthUser user, String tokenId, Instant issuedAt, Instant expiresAt, String clientIp) {
        return new TokenSession(tokenId, user.userId(), user.username(), user.role(), issuedAt, expiresAt, clientIp);
    }

    private SecretKey secretKey() {
        byte[] bytes = properties.getJwtSecret().getBytes(StandardCharsets.UTF_8);
        if (bytes.length < 32) {
            byte[] padded = new byte[32];
            System.arraycopy(bytes, 0, padded, 0, bytes.length);
            bytes = padded;
        }
        return Keys.hmacShaKeyFor(bytes);
    }

    private static String stringClaim(Claims claims, String key) {
        Object value = claims.get(key);
        return value == null ? "" : String.valueOf(value);
    }
}
