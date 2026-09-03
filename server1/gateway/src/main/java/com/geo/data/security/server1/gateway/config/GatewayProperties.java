package com.geo.data.security.server1.gateway.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.ArrayList;
import java.util.List;

@ConfigurationProperties(prefix = "gateway")
public class GatewayProperties {

    private String environment = "test";
    private Security security = new Security();
    private RateLimit rateLimit = new RateLimit();
    private Cors cors = new Cors();
    private AccessPolicy accessPolicy = new AccessPolicy();

    public String getEnvironment() {
        return environment;
    }

    public void setEnvironment(String environment) {
        this.environment = environment;
    }

    public Security getSecurity() {
        return security;
    }

    public void setSecurity(Security security) {
        this.security = security;
    }

    public RateLimit getRateLimit() {
        return rateLimit;
    }

    public void setRateLimit(RateLimit rateLimit) {
        this.rateLimit = rateLimit;
    }

    public Cors getCors() {
        return cors;
    }

    public void setCors(Cors cors) {
        this.cors = cors;
    }

    public AccessPolicy getAccessPolicy() {
        return accessPolicy;
    }

    public void setAccessPolicy(AccessPolicy accessPolicy) {
        this.accessPolicy = accessPolicy;
    }

    public static class Security {
        /** JWT 密钥，生产必须外置，禁止写死真实密钥到仓库 */
        private String jwtSecret = "LOCAL_DEV_ONLY_CHANGE_ME_32CHARS_MIN";
        private long tokenTtlSeconds = 28800;
        private boolean tlsEnabled = false;
        private List<String> publicPaths = new ArrayList<>(List.of(
                "/api/health",
                "/api/ready",
                "/api/auth/login",
                "/actuator/health"
        ));

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

        public boolean isTlsEnabled() {
            return tlsEnabled;
        }

        public void setTlsEnabled(boolean tlsEnabled) {
            this.tlsEnabled = tlsEnabled;
        }

        public List<String> getPublicPaths() {
            return publicPaths;
        }

        public void setPublicPaths(List<String> publicPaths) {
            this.publicPaths = publicPaths;
        }
    }

    public static class RateLimit {
        private boolean enabled = true;
        /** 每终端/IP 每分钟请求上限（对标工业网关流量整形） */
        private int requestsPerMinutePerIp = 120;
        private int requestsPerMinutePerUser = 180;
        private int burst = 30;

        public boolean isEnabled() {
            return enabled;
        }

        public void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }

        public int getRequestsPerMinutePerIp() {
            return requestsPerMinutePerIp;
        }

        public void setRequestsPerMinutePerIp(int requestsPerMinutePerIp) {
            this.requestsPerMinutePerIp = requestsPerMinutePerIp;
        }

        public int getRequestsPerMinutePerUser() {
            return requestsPerMinutePerUser;
        }

        public void setRequestsPerMinutePerUser(int requestsPerMinutePerUser) {
            this.requestsPerMinutePerUser = requestsPerMinutePerUser;
        }

        public int getBurst() {
            return burst;
        }

        public void setBurst(int burst) {
            this.burst = burst;
        }
    }

    public static class Cors {
        private List<String> allowedOrigins = new ArrayList<>(List.of(
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5174",
                "http://localhost:5175",
                "http://127.0.0.1:5175"
        ));

        public List<String> getAllowedOrigins() {
            return allowedOrigins;
        }

        public void setAllowedOrigins(List<String> allowedOrigins) {
            this.allowedOrigins = allowedOrigins;
        }
    }

    public static class AccessPolicy {
        /** 禁止终端经网关探测的敏感路径片段 */
        private List<String> blockedPathPatterns = new ArrayList<>(List.of(
                "/actuator/env",
                "/actuator/beans",
                "/actuator/mappings",
                "/.git",
                "/server2",
                "/veracrypt",
                "/elasticsearch",
                "/fisco"
        ));
        private int maxUploadSizeGb = 50;
        private int maxTerminals = 11;

        public List<String> getBlockedPathPatterns() {
            return blockedPathPatterns;
        }

        public void setBlockedPathPatterns(List<String> blockedPathPatterns) {
            this.blockedPathPatterns = blockedPathPatterns;
        }

        public int getMaxUploadSizeGb() {
            return maxUploadSizeGb;
        }

        public void setMaxUploadSizeGb(int maxUploadSizeGb) {
            this.maxUploadSizeGb = maxUploadSizeGb;
        }

        public int getMaxTerminals() {
            return maxTerminals;
        }

        public void setMaxTerminals(int maxTerminals) {
            this.maxTerminals = maxTerminals;
        }
    }
}
