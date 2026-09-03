package com.geo.data.security.server1.gateway.filter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.geo.data.security.server1.gateway.config.GatewayProperties;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiResponse;
import com.geo.data.security.server1.common.error.ErrorCode;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * 南北向隔离：拦截敏感路径探测，防止终端经网关触达管理面/内部系统。
 */
public class SecurityGuardFilter extends OncePerRequestFilter {

    private final GatewayProperties properties;
    private final ObjectMapper objectMapper;

    public SecurityGuardFilter(GatewayProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        String path = request.getRequestURI().toLowerCase();
        for (String blocked : properties.getAccessPolicy().getBlockedPathPatterns()) {
            if (path.contains(blocked.toLowerCase())) {
                writeForbidden(response);
                return;
            }
        }
        if (path.contains("..") || path.contains("%2e%2e")) {
            writeForbidden(response);
            return;
        }
        filterChain.doFilter(request, response);
    }

    private void writeForbidden(HttpServletResponse response) throws IOException {
        response.setStatus(HttpServletResponse.SC_FORBIDDEN);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        objectMapper.writeValue(response.getOutputStream(),
                ApiResponse.fail(ErrorCode.PATH_BLOCKED, RequestContext.requestId()));
    }
}
