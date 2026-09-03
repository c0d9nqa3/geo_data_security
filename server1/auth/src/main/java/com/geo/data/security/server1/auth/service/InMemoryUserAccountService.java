package com.geo.data.security.server1.auth.service;

import com.geo.data.security.server1.auth.model.AuthUser;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 测试/无库环境的内存用户。本地联调默认走 JDBC（见 gateway）。
 */
@Service
@ConditionalOnProperty(name = "auth.user-store", havingValue = "memory")
public class InMemoryUserAccountService implements UserAccountService {

    private final Map<String, AuthUser> users = new ConcurrentHashMap<>();

    public InMemoryUserAccountService() {
        users.put("admin", new AuthUser(
                "u_admin",
                "admin",
                "admin123",
                "系统管理员",
                "admin",
                Set.of("upload", "project", "task", "review", "download", "trace", "audit"),
                true
        ));
        users.put("operator", new AuthUser(
                "u_operator",
                "operator",
                "operator123",
                "业务操作员",
                "operator",
                Set.of("upload", "project", "task", "download", "trace"),
                true
        ));
    }

    @Override
    public Optional<AuthUser> findByUsername(String username) {
        if (username == null) {
            return Optional.empty();
        }
        return Optional.ofNullable(users.get(username.trim().toLowerCase()));
    }
}
