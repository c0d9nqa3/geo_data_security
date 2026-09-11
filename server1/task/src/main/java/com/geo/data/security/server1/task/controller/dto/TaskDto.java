package com.geo.data.security.server1.task.controller.dto;

import java.util.List;

public record TaskDto(
        String id,
        String applyType,
        String title,
        String projectId,
        String projectName,
        String fileId,
        String fileName,
        String applyUserId,
        String applyUser,
        String reviewUser,
        String status,
        String stage,
        String currentNode,
        String currentNodeLabel,
        int progress,
        String circulationStatus,
        String distributeStatus,
        String comment,
        String purpose,
        int urgeCount,
        String lastUrgeAt,
        boolean canUrge,
        boolean canRetry,
        boolean canWithdraw,
        boolean canDelete,
        boolean canDistribute,
        List<TaskNodeDto> nodes,
        String createdAt,
        String updatedAt,
        String type,
        String resultId,
        boolean outputReady
) {
}
