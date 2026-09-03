package com.geo.data.security.server1.auth.controller.dto;

public record LoginResultDto(
        String token,
        UserInfoDto user
) {
}
