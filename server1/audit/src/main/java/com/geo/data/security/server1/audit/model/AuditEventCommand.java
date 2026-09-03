package com.geo.data.security.server1.audit.model;

/**
 * 业务审计事件命令，字段对齐 {@code shared/events}。
 * 不包含链上私钥；哈希仅为摘要。
 */
public record AuditEventCommand(
        String action,
        String projectId,
        String fileId,
        String taskId,
        String resultId,
        String detail,
        String resultStatus,
        String sourceHash,
        String resultHash
) {
    public static AuditEventCommand of(String action, String projectId, String fileId, String taskId,
                                       String detail, String resultStatus) {
        return new AuditEventCommand(action, projectId, fileId, taskId, null, detail, resultStatus, null, null);
    }
}
