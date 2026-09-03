package com.geo.data.security.server1.task.service;

import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.circulation.service.CirculationIntake;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.common.support.Checks;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.task.controller.dto.CreateTaskRequest;
import com.geo.data.security.server1.task.controller.dto.TaskDto;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.List;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "jdbc", matchIfMissing = true)
public class JdbcTaskService implements TaskService {

    private final JdbcTemplate jdbc;
    private final AuditRecorder auditRecorder;
    private final CirculationIntake circulationIntake;

    public JdbcTaskService(JdbcTemplate jdbcTemplate, AuditRecorder auditRecorder,
                           CirculationIntake circulationIntake) {
        this.jdbc = jdbcTemplate;
        this.auditRecorder = auditRecorder;
        this.circulationIntake = circulationIntake;
    }

    @Override
    public List<TaskDto> listTasks(String projectId) {
        RequestContext.requirePrincipal();
        boolean filter = projectId != null && !projectId.isBlank();
        String sql = """
                SELECT t.task_id, t.project_id, p.project_name, t.file_id, f.file_name,
                       t.task_type, t.status, t.progress, t.created_at, t.updated_at,
                       COALESCE(u.display_name, t.created_by) AS creator_name
                FROM biz_task t
                LEFT JOIN biz_project p ON p.project_id = t.project_id
                LEFT JOIN biz_file f ON f.file_id = t.file_id
                LEFT JOIN sys_user u ON u.user_id = t.created_by
                """ + (filter ? " WHERE t.project_id = ? " : " ") + """
                ORDER BY COALESCE(t.updated_at, t.created_at) DESC, t.id DESC
                """;
        return filter
                ? jdbc.query(sql, this::mapTask, projectId)
                : jdbc.query(sql, this::mapTask);
    }

    @Override
    @Transactional
    public TaskDto createTask(CreateTaskRequest request) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        String fileId = Checks.requireText(request.fileId(), "请选择关联文件");
        String type = Checks.requireText(request.type(), "请选择任务类型");

        List<FileRef> files = jdbc.query(
                """
                SELECT f.file_id, f.project_id, f.file_name, p.project_name
                FROM biz_file f
                LEFT JOIN biz_project p ON p.project_id = f.project_id
                WHERE f.file_id = ?
                LIMIT 1
                """,
                (rs, i) -> new FileRef(
                        rs.getString("file_id"),
                        rs.getString("project_id"),
                        rs.getString("file_name"),
                        rs.getString("project_name")
                ),
                fileId
        );
        if (files.isEmpty()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "关联文件不存在");
        }
        FileRef file = files.get(0);
        String taskId = "task_" + System.currentTimeMillis();
        LocalDateTime now = LocalDateTime.now();
        jdbc.update(
                """
                INSERT INTO biz_task
                  (task_id, project_id, file_id, task_type, status, progress, created_by, updated_at)
                VALUES (?, ?, ?, ?, 'waiting_review', 0, ?, ?)
                """,
                taskId, file.projectId(), file.fileId(), type, principal.userId(), Timestamp.valueOf(now)
        );
        auditRecorder.record("submit_task", file.projectId(), file.fileId(), taskId,
                "提交任务 " + taskId + "（" + type + "）", "success");
        circulationIntake.openTicket("task", file.projectId(), file.fileId(), taskId,
                "提交任务审核：" + type);
        String stamp = TimeFormats.DISPLAY.format(now);
        return new TaskDto(taskId, file.projectId(), TimeFormats.nullToEmpty(file.projectName()),
                file.fileId(), file.fileName(), type, "queued", 0,
                principal.displayName(), stamp, stamp);
    }

    private TaskDto mapTask(java.sql.ResultSet rs, int i) throws java.sql.SQLException {
        Timestamp updated = rs.getTimestamp("updated_at");
        Timestamp created = rs.getTimestamp("created_at");
        return new TaskDto(
                rs.getString("task_id"),
                rs.getString("project_id"),
                TimeFormats.nullToEmpty(rs.getString("project_name")),
                rs.getString("file_id"),
                TimeFormats.nullToEmpty(rs.getString("file_name")),
                rs.getString("task_type"),
                rs.getString("status"),
                rs.getInt("progress"),
                rs.getString("creator_name"),
                TimeFormats.format(created),
                TimeFormats.format(updated != null ? updated : created)
        );
    }

    private record FileRef(String fileId, String projectId, String fileName, String projectName) {
    }
}
