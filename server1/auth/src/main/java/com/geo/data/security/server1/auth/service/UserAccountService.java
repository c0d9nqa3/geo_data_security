package com.geo.data.security.server1.auth.service;

import com.geo.data.security.server1.auth.model.AuthUser;

import java.util.Optional;

/**
 * 用户账号查询。由内存实现或 JDBC 实现提供。
 */
public interface UserAccountService {

    Optional<AuthUser> findByUsername(String username);
}
