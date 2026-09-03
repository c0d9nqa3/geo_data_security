package com.geo.data.security.server1.common.support;

import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;

public final class Checks {

    private Checks() {
    }

    public static String requireText(String value, String message) {
        if (value == null || value.isBlank()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, message);
        }
        return value.trim();
    }

    public static void requirePermission(AccessPrincipal principal, String permCode) {
        if (principal == null || !principal.hasPermission(permCode)) {
            throw new ApiException(ErrorCode.FORBIDDEN, "无权执行该操作");
        }
    }
}
