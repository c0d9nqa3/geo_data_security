package com.geo.data.security.server1.audit.service;

import com.geo.data.security.server1.audit.model.AuditEventCommand;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.UUID;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "jdbc", matchIfMissing = true)
public class JdbcAuditRecorder implements AuditRecorder {

    private final JdbcTemplate jdbc;

    public JdbcAuditRecorder(JdbcTemplate jdbcTemplate) {
        this.jdbc = jdbcTemplate;
    }

    @Override
    public void record(AuditEventCommand command) {
        AccessPrincipal principal = RequestContext.principal();
        String actorUserId = principal == null ? null : principal.userId();
        String actorName = principal == null ? "系统" : principal.displayName();
        String auditId = "aud_" + UUID.randomUUID().toString().replace("-", "").substring(0, 16);
        String detail = command.detail() == null ? "" : command.detail();
        if (command.sourceHash() != null && !command.sourceHash().isBlank()) {
            detail = detail + " sourceHash=" + command.sourceHash();
        }
        if (command.resultHash() != null && !command.resultHash().isBlank()) {
            detail = detail + " resultHash=" + command.resultHash();
        }
        if (detail.length() > 512) {
            detail = detail.substring(0, 512);
        }
        jdbc.update(
                """
                INSERT INTO biz_audit_event
                  (audit_event_id, event_time, actor_user_id, actor_name, action,
                   project_id, file_id, task_id, result_id, detail, result_status, client_ip, request_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                auditId,
                Timestamp.valueOf(LocalDateTime.now()),
                actorUserId,
                actorName,
                command.action(),
                command.projectId(),
                command.fileId(),
                command.taskId(),
                command.resultId(),
                detail,
                command.resultStatus(),
                RequestContext.clientIp(),
                RequestContext.requestId()
        );
    }
}
