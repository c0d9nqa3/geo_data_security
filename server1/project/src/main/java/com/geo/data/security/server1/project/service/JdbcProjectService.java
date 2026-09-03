package com.geo.data.security.server1.project.service;

import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.circulation.service.CirculationIntake;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.common.support.Checks;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.project.controller.dto.CreateProjectRequest;
import com.geo.data.security.server1.project.controller.dto.ProjectDto;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.List;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "jdbc", matchIfMissing = true)
public class JdbcProjectService implements ProjectService {

    private final JdbcTemplate jdbc;
    private final AuditRecorder auditRecorder;
    private final CirculationIntake circulationIntake;

    public JdbcProjectService(JdbcTemplate jdbcTemplate, AuditRecorder auditRecorder,
                              CirculationIntake circulationIntake) {
        this.jdbc = jdbcTemplate;
        this.auditRecorder = auditRecorder;
        this.circulationIntake = circulationIntake;
    }

    @Override
    public List<ProjectDto> listProjects() {
        RequestContext.requirePrincipal();
        return jdbc.query(
                """
                SELECT p.project_id, p.project_name, p.project_code, p.status, p.description,
                       COALESCE(p.updated_at, p.created_at) AS touch_at,
                       COALESCE(ou.display_name, p.owner_user_id) AS owner_name,
                       (SELECT COUNT(*) FROM biz_project_member m WHERE m.project_id = p.project_id) AS member_count,
                       (SELECT COUNT(*) FROM biz_file f WHERE f.project_id = p.project_id) AS file_count
                FROM biz_project p
                LEFT JOIN sys_user ou ON ou.user_id = p.owner_user_id
                ORDER BY COALESCE(p.updated_at, p.created_at) DESC, p.id DESC
                """,
                (rs, i) -> new ProjectDto(
                        rs.getString("project_id"),
                        rs.getString("project_name"),
                        rs.getString("project_code"),
                        rs.getString("status"),
                        rs.getString("owner_name"),
                        rs.getInt("member_count"),
                        rs.getInt("file_count"),
                        TimeFormats.format(rs.getTimestamp("touch_at")),
                        TimeFormats.nullToEmpty(rs.getString("description"))
                )
        );
    }

    @Override
    @Transactional
    public ProjectDto createProject(CreateProjectRequest request) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        String name = Checks.requireText(request.name(), "项目名称不能为空");
        String code = Checks.requireText(request.code(), "项目编号不能为空");
        String description = request.description() == null ? "" : request.description().trim();

        Integer exists = jdbc.queryForObject(
                "SELECT COUNT(*) FROM biz_project WHERE project_code = ?",
                Integer.class,
                code
        );
        if (exists != null && exists > 0) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "项目编号已存在");
        }

        String projectId = "prj_" + System.currentTimeMillis();
        LocalDateTime now = LocalDateTime.now();
        jdbc.update(
                """
                INSERT INTO biz_project
                  (project_id, project_code, project_name, description, status, owner_user_id, updated_at)
                VALUES (?, ?, ?, ?, 'draft', ?, ?)
                """,
                projectId, code, name, description, principal.userId(), Timestamp.valueOf(now)
        );
        jdbc.update(
                """
                INSERT INTO biz_project_member (project_id, user_id, member_role)
                VALUES (?, ?, 'owner')
                """,
                projectId, principal.userId()
        );
        auditRecorder.record("create_project", projectId, null, null,
                "创建项目 " + code + "（" + name + "）", "success");
        circulationIntake.openTicket("project", projectId, null, null, "新建项目审核：" + name);
        return new ProjectDto(projectId, name, code, "draft", principal.displayName(),
                1, 0, TimeFormats.DISPLAY.format(now), description);
    }
}
