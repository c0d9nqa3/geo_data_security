package com.geo.data.security.server1.auth.service;

import com.geo.data.security.server1.auth.model.AuthUser;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

/**
 * 从 MySQL sys_user / 角色权限表加载登录账号。
 */
@Service
@ConditionalOnProperty(name = "auth.user-store", havingValue = "jdbc", matchIfMissing = true)
public class JdbcUserAccountService implements UserAccountService {

    private final JdbcTemplate jdbc;

    public JdbcUserAccountService(JdbcTemplate jdbcTemplate) {
        this.jdbc = jdbcTemplate;
    }

    @Override
    public Optional<AuthUser> findByUsername(String username) {
        if (username == null || username.isBlank()) {
            return Optional.empty();
        }
        String key = username.trim();
        List<AuthUser> rows = jdbc.query(
                """
                SELECT u.user_id, u.username, u.password, u.display_name, u.status,
                       COALESCE((
                         SELECT ur.role_code FROM sys_user_role ur
                         WHERE ur.user_id = u.user_id
                         ORDER BY ur.id ASC LIMIT 1
                       ), 'viewer') AS role_code
                FROM sys_user u
                WHERE u.username = ?
                LIMIT 1
                """,
                (rs, i) -> {
                    String userId = rs.getString("user_id");
                    return new AuthUser(
                            userId,
                            rs.getString("username"),
                            rs.getString("password"),
                            rs.getString("display_name"),
                            rs.getString("role_code"),
                            loadPermissions(userId),
                            rs.getInt("status") == 1
                    );
                },
                key
        );
        return rows.stream().findFirst();
    }

    private Set<String> loadPermissions(String userId) {
        List<String> codes = jdbc.queryForList(
                """
                SELECT DISTINCT rp.perm_code
                FROM sys_user_role ur
                INNER JOIN sys_role_permission rp ON ur.role_code = rp.role_code
                WHERE ur.user_id = ?
                """,
                String.class,
                userId
        );
        return new HashSet<>(codes);
    }
}
