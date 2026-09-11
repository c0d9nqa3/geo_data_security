package com.geo.data.security.server1.task.service;

public record NoticeCommand(
        String type,
        String title,
        String content,
        String circulationId,
        String projectId,
        String projectName,
        String fileId,
        String applyType,
        String senderUserId,
        String senderName
) {
}
