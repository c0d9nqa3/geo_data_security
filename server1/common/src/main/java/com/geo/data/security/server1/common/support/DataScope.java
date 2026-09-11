package com.geo.data.security.server1.common.support;

import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;

import java.util.List;

/**
 * 普通员工只能看自己提交的数据；持有 review 的管理员可看全部并审批。
 * 审核通过后，提交人或管理员都可以发起向服务器2的分发。
 */
public final class DataScope {

    private DataScope() {
    }

    public static boolean canSeeAll(AccessPrincipal principal) {
        return principal != null && (principal.hasPermission("review") || "admin".equals(principal.role()));
    }

    public static boolean isOwner(AccessPrincipal principal, String ownerUserId) {
        return principal != null && principal.userId() != null && principal.userId().equals(ownerUserId);
    }

    public static void requireVisible(AccessPrincipal principal, String ownerUserId) {
        if (canSeeAll(principal) || isOwner(principal, ownerUserId)) {
            return;
        }
        throw new ApiException(ErrorCode.FORBIDDEN, "无权查看该数据");
    }

    public static void restrictToOwner(StringBuilder where, List<Object> args,
                                       AccessPrincipal principal, String column) {
        if (!canSeeAll(principal)) {
            where.append(" AND ").append(column).append(" = ?");
            args.add(principal.userId());
        }
    }
}
