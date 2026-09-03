package com.geo.data.security.server1.gateway.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.geo.data.security.server1.auth.service.AuthService;
import com.geo.data.security.server1.gateway.filter.AccessLogFilter;
import com.geo.data.security.server1.gateway.filter.AuthFilter;
import com.geo.data.security.server1.gateway.filter.GatewayRequestContextFilter;
import com.geo.data.security.server1.gateway.filter.RateLimitFilter;
import com.geo.data.security.server1.gateway.filter.SecurityGuardFilter;
import com.geo.data.security.server1.gateway.ratelimit.TokenBucketRateLimiter;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;

@Configuration
public class WebConfig {

    @Bean
    public CorsFilter corsFilter(GatewayProperties properties) {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowCredentials(true);
        config.setAllowedOrigins(properties.getCors().getAllowedOrigins());
        config.addAllowedHeader("*");
        config.addAllowedMethod("*");
        config.addExposedHeader("X-Request-Id");
        config.addExposedHeader("X-RateLimit-Remaining");
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }

    @Bean
    public FilterRegistrationBean<GatewayRequestContextFilter> gatewayRequestContextFilterRegistration() {
        return ordered(new GatewayRequestContextFilter(), Ordered.HIGHEST_PRECEDENCE);
    }

    @Bean
    public FilterRegistrationBean<SecurityGuardFilter> securityGuardFilterRegistration(
            GatewayProperties properties, ObjectMapper objectMapper) {
        return ordered(new SecurityGuardFilter(properties, objectMapper), Ordered.HIGHEST_PRECEDENCE + 10);
    }

    @Bean
    public FilterRegistrationBean<AuthFilter> authFilterRegistration(
            GatewayProperties properties, AuthService authService, ObjectMapper objectMapper) {
        return ordered(new AuthFilter(properties, authService, objectMapper), Ordered.HIGHEST_PRECEDENCE + 20);
    }

    @Bean
    public FilterRegistrationBean<RateLimitFilter> rateLimitFilterRegistration(
            GatewayProperties properties, TokenBucketRateLimiter rateLimiter, ObjectMapper objectMapper) {
        return ordered(new RateLimitFilter(properties, rateLimiter, objectMapper), Ordered.HIGHEST_PRECEDENCE + 30);
    }

    @Bean
    public FilterRegistrationBean<AccessLogFilter> accessLogFilterRegistration() {
        return ordered(new AccessLogFilter(), Ordered.HIGHEST_PRECEDENCE + 40);
    }

    private static <T extends jakarta.servlet.Filter> FilterRegistrationBean<T> ordered(T filter, int order) {
        FilterRegistrationBean<T> bean = new FilterRegistrationBean<>();
        bean.setFilter(filter);
        bean.addUrlPatterns("/*");
        bean.setOrder(order);
        return bean;
    }
}
