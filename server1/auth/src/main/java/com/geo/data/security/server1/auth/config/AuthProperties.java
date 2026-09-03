package com.geo.data.security.server1.auth.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "auth")
public class AuthProperties {

    /**
     * memory：本地 JVM 内存会话表（默认，无需 Redis）。
     */
    private String tokenStore = "memory";
    /**
     * memory：演示用户；jdbc：读取 MySQL sys_user。
     */
    private String userStore = "jdbc";
    private String jwtSecret = "LOCAL_DEV_ONLY_CHANGE_ME_32CHARS_MIN";
    private long tokenTtlSeconds = 28800;
    private boolean requireSessionCache = true;

    public String getTokenStore() {
        return tokenStore;
    }

    public void setTokenStore(String tokenStore) {
        this.tokenStore = tokenStore;
    }

    public String getUserStore() {
        return userStore;
    }

    public void setUserStore(String userStore) {
        this.userStore = userStore;
    }

    public String getJwtSecret() {
        return jwtSecret;
    }

    public void setJwtSecret(String jwtSecret) {
        this.jwtSecret = jwtSecret;
    }

    public long getTokenTtlSeconds() {
        return tokenTtlSeconds;
    }

    public void setTokenTtlSeconds(long tokenTtlSeconds) {
        this.tokenTtlSeconds = tokenTtlSeconds;
    }

    public boolean isRequireSessionCache() {
        return requireSessionCache;
    }

    public void setRequireSessionCache(boolean requireSessionCache) {
        this.requireSessionCache = requireSessionCache;
    }
}
