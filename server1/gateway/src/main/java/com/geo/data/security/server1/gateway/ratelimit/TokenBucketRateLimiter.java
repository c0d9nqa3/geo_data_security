package com.geo.data.security.server1.gateway.ratelimit;

import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 简易令牌桶限流（工业互联网网关流量整形能力）。
 * 单机内存实现，后续可替换为 Redis / 集群限流。
 */
@Component
public class TokenBucketRateLimiter {

    private final Map<String, Bucket> buckets = new ConcurrentHashMap<>();

    public boolean tryAcquire(String key, int capacity, int refillPerMinute) {
        Bucket bucket = buckets.computeIfAbsent(key, k -> new Bucket(capacity));
        return bucket.tryAcquire(capacity, refillPerMinute);
    }

    private static final class Bucket {
        private double tokens;
        private long lastRefillNanos;

        private Bucket(int capacity) {
            this.tokens = capacity;
            this.lastRefillNanos = System.nanoTime();
        }

        private synchronized boolean tryAcquire(int capacity, int refillPerMinute) {
            long now = System.nanoTime();
            double elapsedMinutes = (now - lastRefillNanos) / 60_000_000_000.0;
            tokens = Math.min(capacity, tokens + elapsedMinutes * refillPerMinute);
            lastRefillNanos = now;
            if (tokens < 1.0) {
                return false;
            }
            tokens -= 1.0;
            return true;
        }
    }
}
