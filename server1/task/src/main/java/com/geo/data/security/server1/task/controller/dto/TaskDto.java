package com.geo.data.security.server1.task.controller.dto;

public record TaskDto(
        String id,
        String projectId,
        String projectName,
        String fileId,
        String fileName,
        String type,
        String status,
        int progress,
        String createdBy,
        String createdAt,
        String updatedAt
) {
}
