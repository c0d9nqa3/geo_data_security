package com.geo.data.security.server1.auth.model;

import java.time.Instant;

/**
 * 服务端会话缓存条目。JWT 负责携带声明，会话缓存负责吊销与在线状态。
 */
public record TokenSession(
        String tokenId,
        String userId,
        String username,
        String role,
        Instant issuedAt,
        Instant expiresAt,
        String clientIp
) {
    public boolean expired() {
        return Instant.now().isAfter(expiresAt);
    }
}
