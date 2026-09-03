package com.geo.data.security.server1.gateway.filter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.geo.data.security.server1.auth.error.AuthException;
import com.geo.data.security.server1.auth.model.AuthPrincipal;
import com.geo.data.security.server1.auth.service.AuthService;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiResponse;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.gateway.config.GatewayProperties;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * 网关统一鉴权：除白名单外，所有请求必须携带有效 Bearer Token。
 */
public class AuthFilter extends OncePerRequestFilter {

    private final GatewayProperties properties;
    private final AuthService authService;
    private final ObjectMapper objectMapper;
    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    public AuthFilter(GatewayProperties properties, AuthService authService, ObjectMapper objectMapper) {
        this.properties = properties;
        this.authService = authService;
        this.objectMapper = objectMapper;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        if ("OPTIONS".equalsIgnoreCase(request.getMethod()) || isPublic(request.getRequestURI())) {
            filterChain.doFilter(request, response);
            return;
        }

        String header = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (header == null || !header.startsWith("Bearer ")) {
            unauthorized(response);
            return;
        }
        String token = header.substring(7).trim();
        try {
            AuthPrincipal principal = authService.authenticate(token);
            RequestContext.setPrincipal(new AccessPrincipal(
                    principal.userId(),
                    principal.username(),
                    principal.displayName(),
                    principal.role(),
                    principal.permissions()
            ));
            filterChain.doFilter(request, response);
        } catch (AuthException ex) {
            unauthorized(response);
        } catch (Exception ex) {
            unauthorized(response);
        }
    }

    private boolean isPublic(String path) {
        List<String> publicPaths = properties.getSecurity().getPublicPaths();
        for (String pattern : publicPaths) {
            if (pathMatcher.match(pattern, path)) {
                return true;
            }
        }
        return false;
    }

    private void unauthorized(HttpServletResponse response) throws IOException {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        objectMapper.writeValue(response.getOutputStream(),
                ApiResponse.fail(ErrorCode.UNAUTHORIZED, RequestContext.requestId()));
    }
}
