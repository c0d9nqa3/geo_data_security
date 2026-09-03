package com.geo.data.security.server1.audit.service;

import com.geo.data.security.server1.audit.controller.dto.AuditEventDto;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.support.TimeFormats;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "jdbc", matchIfMissing = true)
public class JdbcAuditQueryService implements AuditQueryService {

    private final JdbcTemplate jdbc;

    public JdbcAuditQueryService(JdbcTemplate jdbcTemplate) {
        this.jdbc = jdbcTemplate;
    }

    @Override
    public List<AuditEventDto> listEvents(String action, String resultStatus) {
        RequestContext.requirePrincipal();
        StringBuilder sql = new StringBuilder(
                """
                SELECT audit_event_id, event_time, actor_name, action, project_id, file_id, task_id,
                       result_id, detail, result_status
                FROM biz_audit_event
                WHERE 1=1
                """);
        List<Object> args = new ArrayList<>();
        if (action != null && !action.isBlank()) {
            sql.append(" AND action = ? ");
            args.add(action.trim());
        }
        if (resultStatus != null && !resultStatus.isBlank()) {
            sql.append(" AND result_status = ? ");
            args.add(resultStatus.trim());
        }
        sql.append(" ORDER BY event_time DESC, id DESC LIMIT 200 ");
        return jdbc.query(sql.toString(), (rs, i) -> new AuditEventDto(
                rs.getString("audit_event_id"),
                TimeFormats.format(rs.getTimestamp("event_time")),
                rs.getString("actor_name") == null ? "未知" : rs.getString("actor_name"),
                rs.getString("action"),
                rs.getString("project_id"),
                rs.getString("file_id"),
                rs.getString("task_id"),
                rs.getString("result_id"),
                rs.getString("detail"),
                rs.getString("result_status")
        ), args.toArray());
    }
}
