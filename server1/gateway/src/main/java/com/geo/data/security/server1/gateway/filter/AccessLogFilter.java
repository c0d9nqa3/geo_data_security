package com.geo.data.security.server1.gateway.filter;

import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.util.ContentCachingResponseWrapper;

import java.io.IOException;

/**
 * 终端接入审计日志（工业互联网网关运维可观测能力）。
 * 仅记录业务标识，不写文件路径/密钥。
 */
public class AccessLogFilter extends OncePerRequestFilter {

    private static final Logger ACCESS = LoggerFactory.getLogger("GATEWAY_ACCESS");

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        ContentCachingResponseWrapper wrapped = new ContentCachingResponseWrapper(response);
        try {
            filterChain.doFilter(request, wrapped);
        } finally {
            AccessPrincipal principal = RequestContext.principal();
            ACCESS.info(
                    "requestId={} method={} path={} status={} costMs={} ip={} userId={} role={}",
                    RequestContext.requestId(),
                    request.getMethod(),
                    request.getRequestURI(),
                    wrapped.getStatus(),
                    RequestContext.elapsedMs(),
                    RequestContext.clientIp(),
                    principal == null ? "-" : principal.userId(),
                    principal == null ? "-" : principal.role()
            );
            wrapped.copyBodyToResponse();
        }
    }
}
