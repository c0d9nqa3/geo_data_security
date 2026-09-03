package com.geo.data.security.server1.gateway.controller;

import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiResponse;
import com.geo.data.security.server1.gateway.config.GatewayProperties;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class HealthController {

    private final GatewayProperties properties;

    public HealthController(GatewayProperties properties) {
        this.properties = properties;
    }

    @GetMapping("/health")
    public ApiResponse<Map<String, Object>> health() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("status", "UP");
        body.put("role", "access_control");
        body.put("module", "gateway");
        body.put("environment", properties.getEnvironment());
        return ApiResponse.ok(RequestContext.requestId(), body);
    }

    @GetMapping("/ready")
    public ApiResponse<Map<String, Object>> ready() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("status", "READY");
        body.put("maxTerminals", properties.getAccessPolicy().getMaxTerminals());
        body.put("rateLimitEnabled", properties.getRateLimit().isEnabled());
        return ApiResponse.ok(RequestContext.requestId(), body);
    }
}
