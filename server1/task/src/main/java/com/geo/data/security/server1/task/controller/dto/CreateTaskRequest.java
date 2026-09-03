package com.geo.data.security.server1.task.controller.dto;

import jakarta.validation.constraints.NotBlank;

public record CreateTaskRequest(
        @NotBlank String fileId,
        @NotBlank String type
) {
}
