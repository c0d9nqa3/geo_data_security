package com.geo.data.security.server1.auth.store;

import com.geo.data.security.server1.auth.model.TokenSession;

import java.util.Optional;

/**
 * Token 会话缓存抽象。
 * 本地默认 memory；生产多实例可换成 Redis 实现，不改业务代码。
 */
public interface TokenSessionStore {

    void save(TokenSession session);

    Optional<TokenSession> find(String tokenId);

    void remove(String tokenId);

    void removeByUserId(String userId);
}
