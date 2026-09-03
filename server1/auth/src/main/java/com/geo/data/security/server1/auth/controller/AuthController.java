package com.geo.data.security.server1.auth.controller;

import com.geo.data.security.server1.auth.error.AuthException;
import com.geo.data.security.server1.auth.model.LoginCommand;
import com.geo.data.security.server1.auth.model.LoginResult;
import com.geo.data.security.server1.auth.service.AuthService;
import com.geo.data.security.server1.auth.controller.dto.LoginRequest;
import com.geo.data.security.server1.auth.controller.dto.LoginResultDto;
import com.geo.data.security.server1.auth.controller.dto.UserInfoDto;
import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ApiResponse;
import com.geo.data.security.server1.common.error.ErrorCode;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.HttpHeaders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;
    private final AuditRecorder auditRecorder;

    public AuthController(AuthService authService, AuditRecorder auditRecorder) {
        this.authService = authService;
        this.auditRecorder = auditRecorder;
    }

    @PostMapping("/login")
    public ApiResponse<LoginResultDto> login(@Valid @RequestBody LoginRequest request) {
        try {
            LoginResult result = authService.login(
                    new LoginCommand(request.getUsername(), request.getPassword(), RequestContext.clientIp()));
            AccessPrincipal principal = new AccessPrincipal(
                    result.principal().userId(),
                    result.principal().username(),
                    result.principal().displayName(),
                    result.principal().role(),
                    result.principal().permissions()
            );
            RequestContext.setPrincipal(principal);
            try {
                auditRecorder.record("login", null, null, null, "终端登录成功", "success");
            } catch (Exception ignored) {
                // 审计失败不阻断登录
            }
            UserInfoDto user = new UserInfoDto(
                    principal.userId(),
                    principal.username(),
                    principal.displayName(),
                    principal.role(),
                    principal.permissions()
            );
            return ApiResponse.ok(RequestContext.requestId(), new LoginResultDto(result.token(), user));
        } catch (AuthException ex) {
            if ("AUTH-400".equals(ex.getCode())) {
                throw new ApiException(ErrorCode.BAD_REQUEST, ex.getMessage());
            }
            throw new ApiException(ErrorCode.UNAUTHORIZED, ex.getMessage());
        }
    }

    @GetMapping("/me")
    public ApiResponse<UserInfoDto> me() {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        UserInfoDto user = new UserInfoDto(
                principal.userId(),
                principal.username(),
                principal.displayName(),
                principal.role(),
                principal.permissions()
        );
        return ApiResponse.ok(RequestContext.requestId(), user);
    }

    @PostMapping("/logout")
    public ApiResponse<Void> logout(HttpServletRequest request) {
        String header = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (header == null || !header.startsWith("Bearer ")) {
            throw new ApiException(ErrorCode.UNAUTHORIZED);
        }
        try {
            authService.logout(header.substring(7).trim());
        } catch (AuthException ex) {
            throw new ApiException(ErrorCode.UNAUTHORIZED, ex.getMessage());
        }
        return ApiResponse.ok(RequestContext.requestId(), null);
    }
}
