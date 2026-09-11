package com.geo.data.security.server1.task.controller.dto;

public record TaskResultDto(
        String taskId,
        String resultId,
        String resultHash,
        String chainProof,
        String message
) {
}
