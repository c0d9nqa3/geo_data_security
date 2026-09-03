package com.geo.data.security.server1.circulation.controller.dto;

public record CirculationDto(
        String id,
        String applyType,
        String projectId,
        String projectName,
        String taskId,
        String fileId,
        String fileName,
        String resultId,
        String applyUserId,
        String applyUser,
        String reviewUser,
        String status,
        String purpose,
        String comment,
        String authorizeScope,
        String expireAt,
        String distributeStatus,
        String resultHash,
        String createdAt
) {
}
