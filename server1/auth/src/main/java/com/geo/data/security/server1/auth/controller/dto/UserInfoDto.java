package com.geo.data.security.server1.auth.controller.dto;

import java.util.Set;

public record UserInfoDto(
        String id,
        String username,
        String displayName,
        String role,
        Set<String> permissions
) {
}
