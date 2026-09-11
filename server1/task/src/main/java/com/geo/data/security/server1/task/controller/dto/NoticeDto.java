package com.geo.data.security.server1.task.controller.dto;

public record NoticeDto(
        String id,
        String type,
        String title,
        String content,
        String circulationId,
        String projectId,
        String projectName,
        String fileId,
        String applyType,
        String applyTypeLabel,
        String senderUserId,
        String senderName,
        boolean read,
        String createdAt
) {
}
