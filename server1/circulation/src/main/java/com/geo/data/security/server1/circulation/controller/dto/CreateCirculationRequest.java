package com.geo.data.security.server1.circulation.controller.dto;

public record CreateCirculationRequest(
        String projectId,
        String taskId,
        String purpose,
        String authorizeScope,
        Integer expireHours
) {
}
