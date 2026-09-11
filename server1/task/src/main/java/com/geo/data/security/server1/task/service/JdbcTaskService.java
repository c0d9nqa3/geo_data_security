package com.geo.data.security.server1.task.service;

import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.common.support.Checks;
import com.geo.data.security.server1.common.support.DataScope;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.task.controller.dto.CreateTaskRequest;
import com.geo.data.security.server1.task.controller.dto.TaskDto;
import com.geo.data.security.server1.task.controller.dto.TaskResultDto;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "jdbc", matchIfMissing = true)
public class JdbcTaskService implements TaskService {

    private static final String LIST_SQL = """
            SELECT c.circulation_id, c.apply_type, c.project_id, p.project_name, c.file_id, f.file_name,
                   c.apply_user_id, COALESCE(au.display_name, c.apply_user_id) AS apply_name,
                   ru.display_name AS review_name, c.status, c.distribute_status, c.purpose, c.comment_text,
                   COALESCE(c.urge_count, 0) AS urge_count, c.last_urge_at, c.created_at,
                   COALESCE(c.updated_at, c.created_at) AS touch_at, COALESCE(c.deleted, 0) AS deleted
            FROM biz_circulation c
            LEFT JOIN biz_project p ON p.project_id = c.project_id
            LEFT JOIN biz_file f ON f.file_id = c.file_id
            LEFT JOIN sys_user au ON au.user_id = c.apply_user_id
            LEFT JOIN sys_user ru ON ru.user_id = c.review_user_id
            """;

    private final JdbcTemplate jdbc;
    private final AuditRecorder auditRecorder;
    private final NoticeRecorder noticeRecorder;

    public JdbcTaskService(JdbcTemplate jdbcTemplate, AuditRecorder auditRecorder, NoticeRecorder noticeRecorder) {
        this.jdbc = jdbcTemplate;
        this.auditRecorder = auditRecorder;
        this.noticeRecorder = noticeRecorder;
        ensureWorkflowColumns();
    }

    @Override
    public PageDto<TaskDto> listTasks(String projectId, String applyType, String status,
                                      Integer page, Integer pageSize) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        DataScope.restrictToOwner(where, args, principal, "c.apply_user_id");
        if (projectId != null && !projectId.isBlank()) {
            where.append(" AND c.project_id = ?");
            args.add(projectId.trim());
        }
        if (applyType != null && !applyType.isBlank()) {
            where.append(" AND c.apply_type = ?");
            args.add(applyType.trim());
        }
        appendStatusFilter(where, args, status);
        Long total = jdbc.queryForObject("SELECT COUNT(*) FROM biz_circulation c" + where, Long.class, args.toArray());
        long count = total == null ? 0 : total;
        int size = PageDto.normalizeSize(pageSize);
        int pages = PageDto.totalPages(count, size);
        int current = PageDto.normalizePage(page, pages);
        int offset = (current - 1) * size;
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(offset);
        pageArgs.add(size);
        List<TaskDto> items = jdbc.query(
                LIST_SQL + where + " ORDER BY COALESCE(c.updated_at, c.created_at) DESC, c.id DESC LIMIT ?, ?",
                (rs, i) -> mapTask(rs, principal),
                pageArgs.toArray()
        );
        return PageDto.of(items, count, current, size);
    }

    @Override
    public long countRunning() {
        RequestContext.requirePrincipal();
        Long total = jdbc.queryForObject(
                """
                SELECT COUNT(*) FROM biz_circulation
                WHERE deleted = 0 AND status <> 'withdrawn' AND (
                    status = 'pending'
                    OR (status = 'approved' AND distribute_status <> 'dispatched')
                )
                """,
                Long.class
        );
        return total == null ? 0 : total;
    }

    @Override
    public List<TaskDto> listRecentAll(int limit) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        int size = Math.max(1, Math.min(limit, 50));
        return jdbc.query(
                LIST_SQL + " WHERE c.status <> 'withdrawn' AND COALESCE(c.deleted, 0) = 0 ORDER BY COALESCE(c.updated_at, c.created_at) DESC, c.id DESC LIMIT ?",
                (rs, i) -> mapTask(rs, principal),
                size
        );
    }

    @Override
    public Map<String, Long> countCreatedByDay(LocalDate fromInclusive) {
        RequestContext.requirePrincipal();
        Map<String, Long> map = new LinkedHashMap<>();
        jdbc.query(
                """
                SELECT DATE(created_at) AS d, COUNT(*) AS c
                FROM biz_circulation
                WHERE deleted = 0 AND created_at >= ?
                GROUP BY DATE(created_at)
                """,
                rs -> {
                    java.sql.Date day = rs.getDate("d");
                    if (day != null) {
                        map.put(day.toLocalDate().toString(), rs.getLong("c"));
                    }
                },
                Timestamp.valueOf(fromInclusive.atStartOfDay())
        );
        return map;
    }

    @Override
    public TaskDto getTask(String taskId) {
        return requireTask(taskId);
    }

    @Override
    @Transactional
    public TaskDto urge(String taskId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        TaskDto current = requireTask(taskId);
        if (!current.canUrge()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "当前节点不可催办");
        }
        if (!DataScope.isOwner(principal, current.applyUserId())) {
            throw new ApiException(ErrorCode.FORBIDDEN, "只有发起人可以催办");
        }
        if (current.lastUrgeAt() != null && !current.lastUrgeAt().isBlank()) {
            try {
                LocalDateTime last = LocalDateTime.parse(current.lastUrgeAt(), TimeFormats.DISPLAY);
                if (last.plusMinutes(5).isAfter(LocalDateTime.now())) {
                    throw new ApiException(ErrorCode.BAD_REQUEST, "刚刚已催办，请稍后再试");
                }
            } catch (ApiException e) {
                throw e;
            } catch (Exception ignored) {
                // 时间解析失败则允许催办
            }
        }
        LocalDateTime now = LocalDateTime.now();
        Timestamp ts = Timestamp.valueOf(now);
        jdbc.update(
                """
                UPDATE biz_circulation
                SET urge_count = COALESCE(urge_count, 0) + 1, last_urge_at = ?, updated_at = ?
                WHERE circulation_id = ? AND deleted = 0
                """,
                ts, ts, current.id()
        );
        auditRecorder.record("urge", current.projectId(), current.fileId(), current.id(),
                "发起人催办「" + current.title() + "」，当前节点：" + current.currentNodeLabel(), "success");
        noticeRecorder.notifyReviewers(new NoticeCommand(
                "urge",
                "待审核催办",
                principal.displayName() + "催办" + current.type() + "「" + current.title()
                        + "」，请尽快审核。",
                current.id(),
                current.projectId(),
                current.projectName(),
                current.fileId(),
                current.applyType(),
                principal.userId(),
                principal.displayName()
        ));
        return requireTask(taskId);
    }

    @Override
    @Transactional
    public TaskDto retry(String taskId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        TaskDto current = requireTask(taskId);
        if (!current.canRetry()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "当前状态不可重新提交");
        }
        if (!DataScope.isOwner(principal, current.applyUserId()) && !DataScope.canSeeAll(principal)) {
            throw new ApiException(ErrorCode.FORBIDDEN, "无权重新提交该任务");
        }
        LocalDateTime now = LocalDateTime.now();
        Timestamp ts = Timestamp.valueOf(now);
        jdbc.update(
                """
                UPDATE biz_circulation
                SET status = 'pending', review_user_id = NULL, comment_text = '',
                    distribute_status = 'none', deleted = 0,
                    created_at = ?, expire_at = ?, updated_at = ?
                WHERE circulation_id = ?
                """,
                ts, Timestamp.valueOf(now.plusHours(72)), ts, current.id()
        );
        if ("project".equals(current.applyType()) && current.projectId() != null) {
            jdbc.update("UPDATE biz_project SET status = 'draft', updated_at = ? WHERE project_id = ?",
                    ts, current.projectId());
        }
        if ("file".equals(current.applyType()) && current.fileId() != null) {
            jdbc.update("UPDATE biz_file SET status = 'uploaded', updated_at = ? WHERE file_id = ?",
                    ts, current.fileId());
        }
        String reason = switch (current.status()) {
            case "failed" -> "分发失败后重新提交 ";
            case "withdrawn" -> "撤回后重新提交 ";
            default -> "驳回后重新提交 ";
        };
        auditRecorder.record("resubmit", current.projectId(), current.fileId(), current.id(),
                reason + current.id(), "success");
        auditRecorder.record("apply_circulation", current.projectId(), current.fileId(), current.id(),
                "重新提交待办 " + current.id(), "success");
        return requireTask(taskId);
    }

    @Override
    @Transactional
    public TaskDto withdraw(String taskId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        TaskDto current = requireTask(taskId);
        if (!current.canWithdraw()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "仅未审核的提交可由发起人撤回");
        }
        LocalDateTime now = LocalDateTime.now();
        Timestamp ts = Timestamp.valueOf(now);
        jdbc.update(
                """
                UPDATE biz_circulation
                SET status = 'withdrawn', comment_text = ?, updated_at = ?
                WHERE circulation_id = ? AND status = 'pending' AND deleted = 0
                """,
                "发起人撤回", ts, current.id()
        );
        auditRecorder.record("withdraw", current.projectId(), current.fileId(), current.id(),
                "发起人撤回提交「" + current.title() + "」", "success");
        return requireTask(taskId);
    }

    @Override
    @Transactional
    public TaskDto deleteTask(String taskId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        Checks.requirePermission(principal, "review");
        TaskDto current = requireTask(taskId);
        if (!current.canDelete()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "当前状态不可删除");
        }
        LocalDateTime now = LocalDateTime.now();
        jdbc.update(
                "UPDATE biz_circulation SET deleted = 1, updated_at = ? WHERE circulation_id = ?",
                Timestamp.valueOf(now), current.id()
        );
        auditRecorder.record("delete_circulation", current.projectId(), current.fileId(), current.id(),
                "删除流转单 " + current.id() + "，任务管理仍保留记录", "success");
        return requireTask(taskId);
    }

    @Override
    public TaskDto createTask(CreateTaskRequest request) {
        throw new ApiException(ErrorCode.BAD_REQUEST, "请在项目管理或文件管理中新增提交；任务管理用于查看节点走势、催办和重新提交");
    }

    @Override
    public TaskDto syncFromServer2(String taskId) {
        throw new ApiException(ErrorCode.BAD_REQUEST, "任务管理已改为审批流程跟踪，请到流转控制完成分发");
    }

    @Override
    public TaskDto submitForReview(String taskId) {
        return retry(taskId);
    }

    @Override
    public TaskDto cancelTask(String taskId) {
        return withdraw(taskId);
    }

    @Override
    public TaskResultDto downloadResult(String taskId) {
        throw new ApiException(ErrorCode.BAD_REQUEST, "结果索引请在文件入库并分发完成后由服务器2只读接口提供");
    }

    private TaskDto requireTask(String taskId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        String id = Checks.requireText(taskId, "任务不存在");
        List<TaskDto> found = jdbc.query(LIST_SQL + " WHERE c.circulation_id = ? LIMIT 1",
                (rs, i) -> mapTask(rs, principal), id);
        if (found.isEmpty()) {
            throw new ApiException(ErrorCode.NOT_FOUND, "任务流程不存在");
        }
        TaskDto dto = found.get(0);
        DataScope.requireVisible(principal, dto.applyUserId());
        return dto;
    }

    private TaskDto mapTask(java.sql.ResultSet rs, AccessPrincipal principal) throws java.sql.SQLException {
        return TaskWorkflow.build(
                rs.getString("circulation_id"),
                TimeFormats.nullToEmpty(rs.getString("apply_type")),
                rs.getString("project_id"),
                TimeFormats.nullToEmpty(rs.getString("project_name")),
                rs.getString("file_id"),
                TimeFormats.nullToEmpty(rs.getString("file_name")),
                rs.getString("apply_user_id"),
                TimeFormats.nullToEmpty(rs.getString("apply_name")),
                TimeFormats.nullToEmpty(rs.getString("review_name")),
                rs.getString("status"),
                TimeFormats.nullToEmpty(rs.getString("distribute_status")),
                TimeFormats.nullToEmpty(rs.getString("comment_text")),
                TimeFormats.nullToEmpty(rs.getString("purpose")),
                rs.getInt("urge_count"),
                TimeFormats.format(rs.getTimestamp("last_urge_at")),
                TimeFormats.format(rs.getTimestamp("created_at")),
                TimeFormats.format(rs.getTimestamp("touch_at")),
                rs.getInt("deleted") == 1,
                principal
        );
    }

    private static void appendStatusFilter(StringBuilder where, List<Object> args, String status) {
        if (status == null || status.isBlank()) {
            return;
        }
        String value = status.trim();
        switch (value) {
            case "pending", "waiting_review" -> where.append(" AND c.status = 'pending' AND COALESCE(c.deleted, 0) = 0");
            case "rejected" -> where.append(" AND c.status = 'rejected' AND COALESCE(c.deleted, 0) = 0");
            case "withdrawn" -> where.append(" AND c.status = 'withdrawn' AND COALESCE(c.deleted, 0) = 0");
            case "deleted" -> where.append(" AND COALESCE(c.deleted, 0) = 1");
            case "failed" -> where.append(" AND c.distribute_status = 'failed' AND COALESCE(c.deleted, 0) = 0");
            case "completed", "approved" -> where.append(" AND c.distribute_status = 'dispatched' AND COALESCE(c.deleted, 0) = 0");
            case "distributing", "running" -> where.append(
                    " AND c.status = 'approved' AND COALESCE(c.deleted, 0) = 0 AND c.distribute_status <> 'dispatched' AND c.distribute_status <> 'failed'");
            default -> {
                where.append(" AND c.status = ?");
                args.add(value);
            }
        }
    }

    private void ensureWorkflowColumns() {
        addColumnIfMissing("biz_circulation", "urge_count", "INT NOT NULL DEFAULT 0");
        addColumnIfMissing("biz_circulation", "last_urge_at", "DATETIME NULL");
    }

    private void addColumnIfMissing(String table, String column, String spec) {
        Integer n = jdbc.queryForObject(
                """
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ? AND COLUMN_NAME = ?
                """,
                Integer.class, table, column
        );
        if (n == null || n == 0) {
            jdbc.execute("ALTER TABLE " + table + " ADD COLUMN " + column + " " + spec);
        }
    }
}
