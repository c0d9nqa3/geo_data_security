package com.geo.data.security.server1.circulation.service;

import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.circulation.controller.dto.CirculationDto;
import com.geo.data.security.server1.circulation.controller.dto.CirculationPageDto;
import com.geo.data.security.server1.circulation.controller.dto.CreateCirculationRequest;
import com.geo.data.security.server1.circulation.controller.dto.ReviewActionRequest;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.common.support.Checks;
import com.geo.data.security.server1.common.support.TimeFormats;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "jdbc", matchIfMissing = true)
public class JdbcCirculationService implements CirculationService, CirculationIntake {

    private static final String LIST_SQL = """
            SELECT c.circulation_id, c.apply_type, c.project_id, p.project_name, c.task_id, c.file_id,
                   f.file_name, c.result_id, c.apply_user_id, c.status, c.purpose, c.comment_text,
                   c.authorize_scope, c.expire_at, c.distribute_status, c.created_at,
                   COALESCE(au.display_name, c.apply_user_id) AS apply_name,
                   ru.display_name AS review_name,
                   r.result_hash
            FROM biz_circulation c
            LEFT JOIN biz_project p ON p.project_id = c.project_id
            LEFT JOIN biz_file f ON f.file_id = c.file_id
            LEFT JOIN sys_user au ON au.user_id = c.apply_user_id
            LEFT JOIN sys_user ru ON ru.user_id = c.review_user_id
            LEFT JOIN biz_result_index r ON r.result_id = c.result_id
            """;

    private final JdbcTemplate jdbc;
    private final AuditRecorder auditRecorder;

    public JdbcCirculationService(JdbcTemplate jdbcTemplate, AuditRecorder auditRecorder) {
        this.jdbc = jdbcTemplate;
        this.auditRecorder = auditRecorder;
    }

    @Override
    public CirculationPageDto listCirculations(String status, Integer page, Integer pageSize) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        boolean reviewer = principal.hasPermission("review");
        StringBuilder where = new StringBuilder(" WHERE c.deleted = 0");
        List<Object> args = new ArrayList<>();
        if (!reviewer) {
            where.append(" AND c.apply_user_id = ? AND c.status <> 'pending'");
            args.add(principal.userId());
        }
        if (status != null && !status.isBlank()) {
            where.append(" AND c.status = ?");
            args.add(status.trim());
        }
        Long total = jdbc.queryForObject(
                "SELECT COUNT(*) FROM biz_circulation c" + where,
                Long.class,
                args.toArray()
        );
        long count = total == null ? 0 : total;
        int size = CirculationPageDto.normalizeSize(pageSize);
        int pages = CirculationPageDto.totalPages(count, size);
        int current = CirculationPageDto.normalizePage(page, pages);
        int offset = (current - 1) * size;
        String sql = LIST_SQL + where + " ORDER BY c.created_at DESC, c.id DESC LIMIT ?, ?";
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(offset);
        pageArgs.add(size);
        List<CirculationDto> items = jdbc.query(sql, this::mapCirculation, pageArgs.toArray());
        return new CirculationPageDto(items, count, current, size, pages);
    }

    @Override
    public CirculationDto getCirculation(String circulationId) {
        return loadVisible(circulationId);
    }

    @Override
    @Transactional
    public void openTicket(String applyType, String projectId, String fileId, String taskId, String purpose) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        String type = applyType == null || applyType.isBlank() ? "task" : applyType.trim();
        String circulationId = "cir_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        LocalDateTime now = LocalDateTime.now();
        jdbc.update(
                """
                INSERT INTO biz_circulation
                  (circulation_id, project_id, task_id, file_id, apply_user_id, apply_type,
                   status, purpose, authorize_scope, expire_at, distribute_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, 'project_members', ?, 'none', ?)
                """,
                circulationId, projectId, taskId, fileId, principal.userId(), type,
                purpose == null ? "" : purpose,
                Timestamp.valueOf(now.plusHours(72)),
                Timestamp.valueOf(now)
        );
        auditRecorder.record("apply_circulation", projectId, fileId, taskId,
                "提交" + typeLabel(type) + "待办 " + circulationId, "success");
    }

    @Override
    public CirculationDto apply(CreateCirculationRequest request) {
        throw new ApiException(ErrorCode.BAD_REQUEST, "请在项目管理、文件管理或任务管理中提交，流转待办会自动生成");
    }

    @Override
    @Transactional
    public CirculationDto approve(String circulationId, ReviewActionRequest request) {
        return review(circulationId, "approved", request);
    }

    @Override
    @Transactional
    public CirculationDto reject(String circulationId, ReviewActionRequest request) {
        return review(circulationId, "rejected", request);
    }

    @Override
    @Transactional
    public CirculationDto distribute(String circulationId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        Checks.requirePermission(principal, "review");
        CirculationDto current = loadById(circulationId);
        if (current == null) {
            throw new ApiException(ErrorCode.NOT_FOUND, "流转单不存在");
        }
        if (!"approved".equals(current.status())) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "仅审核通过后可提交分发授权");
        }
        if ("dispatched".equals(current.distributeStatus())) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "分发授权已提交");
        }
        LocalDateTime now = LocalDateTime.now();
        Timestamp ts = Timestamp.valueOf(now);
        String type = current.applyType();
        if ("project".equals(type) && current.projectId() != null) {
            jdbc.update("UPDATE biz_project SET status = 'active', updated_at = ? WHERE project_id = ?",
                    ts, current.projectId());
        }
        if ("file".equals(type) && current.fileId() != null) {
            jdbc.update("UPDATE biz_file SET status = 'transferred', updated_at = ? WHERE file_id = ?",
                    ts, current.fileId());
        }
        if ("task".equals(type) && current.taskId() != null) {
            jdbc.update("UPDATE biz_task SET status = 'running', progress = 10, updated_at = ? WHERE task_id = ?",
                    ts, current.taskId());
        }
        jdbc.update(
                "UPDATE biz_circulation SET distribute_status = 'dispatched', updated_at = ? WHERE circulation_id = ? AND deleted = 0",
                ts, circulationId
        );
        auditRecorder.record("distribute", current.projectId(), current.fileId(), current.taskId(),
                "向服务器2提交" + typeLabel(type) + "授权 " + circulationId, "success");
        return loadById(circulationId);
    }

    @Override
    @Transactional
    public void deleteCirculation(String circulationId) {
        CirculationDto current = loadVisible(circulationId);
        LocalDateTime now = LocalDateTime.now();
        jdbc.update(
                "UPDATE biz_circulation SET deleted = 1, updated_at = ? WHERE circulation_id = ? AND deleted = 0",
                Timestamp.valueOf(now), circulationId
        );
        auditRecorder.record("delete_circulation", current.projectId(), current.fileId(), current.taskId(),
                "逻辑删除流转单 " + circulationId, "success");
    }

    private CirculationDto review(String circulationId, String status, ReviewActionRequest request) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        Checks.requirePermission(principal, "review");
        CirculationDto current = loadById(circulationId);
        if (current == null) {
            throw new ApiException(ErrorCode.NOT_FOUND, "流转单不存在");
        }
        if (!"pending".equals(current.status())) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "该流转单已处理");
        }
        String comment = request == null || request.comment() == null ? "" : request.comment().trim();
        LocalDateTime now = LocalDateTime.now();
        jdbc.update(
                """
                UPDATE biz_circulation
                SET status = ?, review_user_id = ?, comment_text = ?, updated_at = ?
                WHERE circulation_id = ?
                """,
                status, principal.userId(), comment, Timestamp.valueOf(now), circulationId
        );
        String action = "approved".equals(status) ? "approve" : "reject";
        auditRecorder.record(action, current.projectId(), current.fileId(), current.taskId(),
                ("approved".equals(status) ? "通过" : "驳回") + typeLabel(current.applyType())
                        + " " + circulationId, "success");
        return loadById(circulationId);
    }

    private CirculationDto loadVisible(String circulationId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        CirculationDto found = loadById(circulationId);
        if (found == null) {
            throw new ApiException(ErrorCode.NOT_FOUND, "流转单不存在");
        }
        if (principal.hasPermission("review")) {
            return found;
        }
        if (!principal.userId().equals(found.applyUserId()) || "pending".equals(found.status())) {
            throw new ApiException(ErrorCode.FORBIDDEN, "无权查看该待办");
        }
        return found;
    }

    private CirculationDto loadById(String circulationId) {
        List<CirculationDto> found = jdbc.query(
                LIST_SQL + " WHERE c.deleted = 0 AND c.circulation_id = ? LIMIT 1",
                this::mapCirculation,
                circulationId
        );
        return found.isEmpty() ? null : found.get(0);
    }

    private static String typeLabel(String type) {
        if ("project".equals(type)) {
            return "新建项目";
        }
        if ("file".equals(type)) {
            return "上传文件";
        }
        return "提交任务";
    }

    private CirculationDto mapCirculation(java.sql.ResultSet rs, int i) throws java.sql.SQLException {
        return new CirculationDto(
                rs.getString("circulation_id"),
                TimeFormats.nullToEmpty(rs.getString("apply_type")),
                rs.getString("project_id"),
                TimeFormats.nullToEmpty(rs.getString("project_name")),
                rs.getString("task_id"),
                rs.getString("file_id"),
                TimeFormats.nullToEmpty(rs.getString("file_name")),
                rs.getString("result_id"),
                rs.getString("apply_user_id"),
                rs.getString("apply_name"),
                TimeFormats.nullToEmpty(rs.getString("review_name")),
                rs.getString("status"),
                TimeFormats.nullToEmpty(rs.getString("purpose")),
                TimeFormats.nullToEmpty(rs.getString("comment_text")),
                TimeFormats.nullToEmpty(rs.getString("authorize_scope")),
                TimeFormats.format(rs.getTimestamp("expire_at")),
                TimeFormats.nullToEmpty(rs.getString("distribute_status")),
                TimeFormats.nullToEmpty(rs.getString("result_hash")),
                TimeFormats.format(rs.getTimestamp("created_at"))
        );
    }
}
