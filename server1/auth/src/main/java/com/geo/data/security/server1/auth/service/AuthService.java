package com.geo.data.security.server1.auth.service;

import com.geo.data.security.server1.auth.config.AuthProperties;
import com.geo.data.security.server1.auth.error.AuthException;
import com.geo.data.security.server1.auth.model.AuthPrincipal;
import com.geo.data.security.server1.auth.model.AuthUser;
import com.geo.data.security.server1.auth.model.LoginCommand;
import com.geo.data.security.server1.auth.model.LoginResult;
import com.geo.data.security.server1.auth.model.TokenSession;
import com.geo.data.security.server1.auth.store.TokenSessionStore;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class AuthService {

    private final UserAccountService userAccountService;
    private final JwtTokenService jwtTokenService;
    private final TokenSessionStore tokenSessionStore;
    private final AuthProperties properties;
    private final Set<String> revokedTokenIds = ConcurrentHashMap.newKeySet();

    public AuthService(
            UserAccountService userAccountService,
            JwtTokenService jwtTokenService,
            TokenSessionStore tokenSessionStore,
            AuthProperties properties) {
        this.userAccountService = userAccountService;
        this.jwtTokenService = jwtTokenService;
        this.tokenSessionStore = tokenSessionStore;
        this.properties = properties;
    }

    public LoginResult login(LoginCommand command) {
        if (command.username() == null || command.username().isBlank()
                || command.password() == null || command.password().isBlank()) {
            throw new AuthException("AUTH-400", "用户名或密码不能为空");
        }

        AuthUser user = userAccountService.findByUsername(command.username())
                .orElseThrow(() -> new AuthException("AUTH-401", "用户名或密码错误"));
        if (!user.enabled() || user.password() == null || !user.password().equals(command.password())) {
            throw new AuthException("AUTH-401", "用户名或密码错误");
        }

        Instant issuedAt = Instant.now();
        Instant expiresAt = issuedAt.plusSeconds(properties.getTokenTtlSeconds());
        String tokenId = jwtTokenService.newTokenId();
        String token = jwtTokenService.issue(user, tokenId, issuedAt, expiresAt);
        TokenSession session = jwtTokenService.toSession(user, tokenId, issuedAt, expiresAt, command.clientIp());
        tokenSessionStore.save(session);

        AuthPrincipal principal = new AuthPrincipal(
                user.userId(),
                user.username(),
                user.displayName(),
                user.role(),
                user.permissions(),
                tokenId
        );
        return new LoginResult(token, "Bearer", properties.getTokenTtlSeconds(), principal);
    }

    public AuthPrincipal authenticate(String bearerToken) {
        if (bearerToken == null || bearerToken.isBlank()) {
            throw new AuthException("AUTH-401", "未登录或令牌无效");
        }
        AuthPrincipal principal = jwtTokenService.parseAndBuildPrincipal(bearerToken);
        String tokenId = principal.tokenId();
        if (tokenId != null && !tokenId.isBlank() && revokedTokenIds.contains(tokenId)) {
            throw new AuthException("AUTH-401", "会话已失效，请重新登录");
        }
        if (properties.isRequireSessionCache()) {
            if (tokenId == null || tokenId.isBlank()) {
                throw new AuthException("AUTH-401", "令牌与会话不匹配");
            }
            TokenSession session = tokenSessionStore.find(tokenId).orElse(null);
            if (session == null) {
                Instant jwtExp = jwtTokenService.parseClaims(bearerToken).getExpiration().toInstant();
                tokenSessionStore.save(new TokenSession(
                        tokenId,
                        principal.userId(),
                        principal.username(),
                        principal.role(),
                        Instant.now(),
                        jwtExp,
                        ""
                ));
            } else if (!session.userId().equals(principal.userId())) {
                throw new AuthException("AUTH-401", "令牌与会话不匹配");
            }
        }
        return refreshPrincipalFromStore(principal);
    }

    private AuthPrincipal refreshPrincipalFromStore(AuthPrincipal principal) {
        if (principal.username() == null || principal.username().isBlank()) {
            return principal;
        }
        return userAccountService.findByUsername(principal.username())
                .map(user -> new AuthPrincipal(
                        user.userId(),
                        user.username(),
                        user.displayName(),
                        user.role(),
                        user.permissions(),
                        principal.tokenId()
                ))
                .orElse(principal);
    }

    public void logout(String bearerToken) {
        AuthPrincipal principal = jwtTokenService.parseAndBuildPrincipal(bearerToken);
        if (principal.tokenId() != null && !principal.tokenId().isBlank()) {
            revokedTokenIds.add(principal.tokenId());
            tokenSessionStore.remove(principal.tokenId());
        }
    }
}
