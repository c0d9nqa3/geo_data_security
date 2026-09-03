package com.geo.data.security.server1.audit.controller.dto;

public record AuditEventDto(
        String id,
        String time,
        String actor,
        String action,
        String projectId,
        String fileId,
        String taskId,
        String resultId,
        String detail,
        String result
) {
}
