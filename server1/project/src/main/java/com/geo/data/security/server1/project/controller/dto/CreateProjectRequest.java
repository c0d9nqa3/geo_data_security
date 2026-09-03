package com.geo.data.security.server1.project.controller.dto;

import jakarta.validation.constraints.NotBlank;

public record CreateProjectRequest(
        @NotBlank String name,
        @NotBlank String code,
        String description
) {
}
