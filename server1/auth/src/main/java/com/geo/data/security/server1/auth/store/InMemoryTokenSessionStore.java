package com.geo.data.security.server1.auth.store;

import com.geo.data.security.server1.auth.model.TokenSession;

import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 本地内存会话缓存，适合单机开发/演示，无需 Redis。
 * 读取时惰性清理过期项。
 */
public class InMemoryTokenSessionStore implements TokenSessionStore {

    private final Map<String, TokenSession> byTokenId = new ConcurrentHashMap<>();

    @Override
    public void save(TokenSession session) {
        byTokenId.put(session.tokenId(), session);
    }

    @Override
    public Optional<TokenSession> find(String tokenId) {
        TokenSession session = byTokenId.get(tokenId);
        if (session == null) {
            return Optional.empty();
        }
        if (session.expired()) {
            byTokenId.remove(tokenId, session);
            return Optional.empty();
        }
        return Optional.of(session);
    }

    @Override
    public void remove(String tokenId) {
        byTokenId.remove(tokenId);
    }

    @Override
    public void removeByUserId(String userId) {
        byTokenId.entrySet().removeIf(e -> userId.equals(e.getValue().userId()));
    }
}
