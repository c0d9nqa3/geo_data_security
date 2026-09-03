package com.geo.data.security.server1.gateway.filter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiResponse;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.gateway.config.GatewayProperties;
import com.geo.data.security.server1.gateway.ratelimit.TokenBucketRateLimiter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

public class RateLimitFilter extends OncePerRequestFilter {

    private final GatewayProperties properties;
    private final TokenBucketRateLimiter rateLimiter;
    private final ObjectMapper objectMapper;

    public RateLimitFilter(GatewayProperties properties, TokenBucketRateLimiter rateLimiter, ObjectMapper objectMapper) {
        this.properties = properties;
        this.rateLimiter = rateLimiter;
        this.objectMapper = objectMapper;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        if (!properties.getRateLimit().isEnabled()) {
            filterChain.doFilter(request, response);
            return;
        }

        String ip = RequestContext.clientIp() == null ? "unknown" : RequestContext.clientIp();
        int ipLimit = properties.getRateLimit().getRequestsPerMinutePerIp();
        int burst = Math.max(properties.getRateLimit().getBurst(), ipLimit);
        boolean ipOk = rateLimiter.tryAcquire("ip:" + ip, burst, ipLimit);
        if (!ipOk) {
            reject(response);
            return;
        }

        AccessPrincipal principal = RequestContext.principal();
        if (principal != null) {
            int userLimit = properties.getRateLimit().getRequestsPerMinutePerUser();
            boolean userOk = rateLimiter.tryAcquire("user:" + principal.userId(),
                    Math.max(properties.getRateLimit().getBurst(), userLimit), userLimit);
            if (!userOk) {
                reject(response);
                return;
            }
        }

        response.setHeader("X-RateLimit-Limit", String.valueOf(ipLimit));
        filterChain.doFilter(request, response);
    }

    private void reject(HttpServletResponse response) throws IOException {
        response.setStatus(429);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setHeader("Retry-After", "60");
        objectMapper.writeValue(response.getOutputStream(),
                ApiResponse.fail(ErrorCode.TOO_MANY_REQUESTS, RequestContext.requestId()));
    }
}
