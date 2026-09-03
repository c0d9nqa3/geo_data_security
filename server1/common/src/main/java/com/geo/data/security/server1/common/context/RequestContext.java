package com.geo.data.security.server1.common.context;

import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;

public final class RequestContext {

    private static final ThreadLocal<String> REQUEST_ID = new ThreadLocal<>();
    private static final ThreadLocal<String> CLIENT_IP = new ThreadLocal<>();
    private static final ThreadLocal<AccessPrincipal> PRINCIPAL = new ThreadLocal<>();
    private static final ThreadLocal<Long> START_NANOS = new ThreadLocal<>();

    private RequestContext() {
    }

    public static void begin(String requestId, String clientIp) {
        REQUEST_ID.set(requestId);
        CLIENT_IP.set(clientIp);
        START_NANOS.set(System.nanoTime());
    }

    public static void setPrincipal(AccessPrincipal principal) {
        PRINCIPAL.set(principal);
    }

    public static String requestId() {
        return REQUEST_ID.get();
    }

    public static String clientIp() {
        return CLIENT_IP.get();
    }

    public static AccessPrincipal principal() {
        return PRINCIPAL.get();
    }

    public static AccessPrincipal requirePrincipal() {
        AccessPrincipal principal = PRINCIPAL.get();
        if (principal == null) {
            throw new ApiException(ErrorCode.UNAUTHORIZED);
        }
        return principal;
    }

    public static long elapsedMs() {
        Long start = START_NANOS.get();
        if (start == null) {
            return 0L;
        }
        return (System.nanoTime() - start) / 1_000_000L;
    }

    public static void clear() {
        REQUEST_ID.remove();
        CLIENT_IP.remove();
        PRINCIPAL.remove();
        START_NANOS.remove();
    }
}
