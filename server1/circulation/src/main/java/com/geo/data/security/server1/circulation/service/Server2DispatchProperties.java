package com.geo.data.security.server1.circulation.service;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "server2.dispatch")
public class Server2DispatchProperties {

    private boolean enabled = true;
    private String baseUrl = "http://10.1.1.121:9081";
    private String token = "";
    /** 可选：对接 Server2 /admin/*，由环境变量 GDS_SERVER2_ADMIN_TOKEN 注入。 */
    private String adminToken = "";
    private int chunkSizeBytes = 64 * 1024 * 1024;
    private int chunkConcurrency = 4;
    private long connectTimeoutMs = 15_000;
    private long requestTimeoutMs = 600_000;
    private long pollIntervalMs = 2_000;
    private long pollTimeoutMs = 1_800_000;

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    public String getToken() {
        return token;
    }

    public void setToken(String token) {
        this.token = token;
    }

    public String getAdminToken() {
        return adminToken;
    }

    public void setAdminToken(String adminToken) {
        this.adminToken = adminToken;
    }

    public int getChunkSizeBytes() {
        return chunkSizeBytes;
    }

    public void setChunkSizeBytes(int chunkSizeBytes) {
        this.chunkSizeBytes = chunkSizeBytes;
    }

    public int getChunkConcurrency() {
        return chunkConcurrency;
    }

    public void setChunkConcurrency(int chunkConcurrency) {
        this.chunkConcurrency = chunkConcurrency;
    }

    public long getConnectTimeoutMs() {
        return connectTimeoutMs;
    }

    public void setConnectTimeoutMs(long connectTimeoutMs) {
        this.connectTimeoutMs = connectTimeoutMs;
    }

    public long getRequestTimeoutMs() {
        return requestTimeoutMs;
    }

    public void setRequestTimeoutMs(long requestTimeoutMs) {
        this.requestTimeoutMs = requestTimeoutMs;
    }

    public long getPollIntervalMs() {
        return pollIntervalMs;
    }

    public void setPollIntervalMs(long pollIntervalMs) {
        this.pollIntervalMs = pollIntervalMs;
    }

    public long getPollTimeoutMs() {
        return pollTimeoutMs;
    }

    public void setPollTimeoutMs(long pollTimeoutMs) {
        this.pollTimeoutMs = pollTimeoutMs;
    }
}
