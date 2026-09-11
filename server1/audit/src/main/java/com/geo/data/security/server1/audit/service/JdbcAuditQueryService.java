package com.geo.data.security.server1.audit.service;

import com.geo.data.security.server1.audit.controller.dto.AuditEventDto;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.common.web.PageDto;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "jdbc", matchIfMissing = true)
public class JdbcAuditQueryService implements AuditQueryService {

    private final JdbcTemplate jdbc;

    public JdbcAuditQueryService(JdbcTemplate jdbcTemplate) {
        this.jdbc = jdbcTemplate;
    }

    @Override
    public PageDto<AuditEventDto> listEvents(String action, String resultStatus, Integer page, Integer pageSize) {
        RequestContext.requirePrincipal();
        StringBuilder where = new StringBuilder(" WHERE action NOT IN ('login', 'logout')");
        List<Object> args = new ArrayList<>();
        if (action != null && !action.isBlank()) {
            where.append(" AND action = ?");
            args.add(action.trim());
        }
        if (resultStatus != null && !resultStatus.isBlank()) {
            where.append(" AND result_status = ?");
            args.add(resultStatus.trim());
        }
        Long total = jdbc.queryForObject(
                "SELECT COUNT(*) FROM biz_audit_event" + where, Long.class, args.toArray());
        long count = total == null ? 0 : total;
        int size = PageDto.normalizeSize(pageSize);
        int pages = PageDto.totalPages(count, size);
        int current = PageDto.normalizePage(page, pages);
        int offset = (current - 1) * size;
        String sql = """
                SELECT audit_event_id, event_time, actor_name, action, project_id, file_id, task_id,
                       result_id, detail, result_status
                FROM biz_audit_event
                """ + where + " ORDER BY event_time DESC, id DESC LIMIT ?, ?";
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(offset);
        pageArgs.add(size);
        List<AuditEventDto> items = jdbc.query(sql, (rs, i) -> new AuditEventDto(
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
        ), pageArgs.toArray());
        return PageDto.of(items, count, current, size);
    }

    @Override
    public Map<String, Long> countByDay(LocalDate fromInclusive) {
        RequestContext.requirePrincipal();
        Timestamp from = Timestamp.valueOf(fromInclusive.atStartOfDay());
        Map<String, Long> map = new LinkedHashMap<>();
        jdbc.query(
                """
                SELECT DATE(event_time) AS d, COUNT(*) AS c
                FROM biz_audit_event
                WHERE action NOT IN ('login', 'logout') AND event_time >= ?
                GROUP BY DATE(event_time)
                """,
                rs -> {
                    java.sql.Date day = rs.getDate("d");
                    if (day != null) {
                        map.put(day.toLocalDate().toString(), rs.getLong("c"));
                    }
                },
                from
        );
        return map;
    }
}
