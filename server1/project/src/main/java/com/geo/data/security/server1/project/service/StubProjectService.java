package com.geo.data.security.server1.project.service;

import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.circulation.service.CirculationIntake;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.support.Checks;
import com.geo.data.security.server1.common.support.DataScope;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.project.controller.dto.CreateProjectRequest;
import com.geo.data.security.server1.project.controller.dto.ProjectDto;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "stub")
public class StubProjectService implements ProjectService {

    private final List<ProjectDto> projects = new CopyOnWriteArrayList<>(List.of(
            new ProjectDto("prj_1001", "城区正射影像库", "DOM-2026-01", "active", "张工", 5, 12,
                    "2026-09-01 16:20", "城区正射影像采集与水印处理项目")
    ));
    private final Map<String, String> owners = new ConcurrentHashMap<>(Map.of("prj_1001", "u_admin"));
    private final AuditRecorder auditRecorder;
    private final CirculationIntake circulationIntake;

    public StubProjectService(AuditRecorder auditRecorder, CirculationIntake circulationIntake) {
        this.auditRecorder = auditRecorder;
        this.circulationIntake = circulationIntake;
    }

    @Override
    public PageDto<ProjectDto> listProjects(String keyword, Integer page, Integer pageSize) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        String q = keyword == null ? "" : keyword.trim().toLowerCase();
        List<ProjectDto> filtered = projects.stream()
                .filter(p -> DataScope.canSeeAll(principal) || DataScope.isOwner(principal, owners.get(p.id())))
                .filter(p -> q.isBlank() || p.name().toLowerCase().contains(q) || p.code().toLowerCase().contains(q))
                .toList();
        return PageDto.slice(filtered, page, pageSize);
    }

    @Override
    public long countAll() {
        RequestContext.requirePrincipal();
        return projects.size();
    }

    @Override
    public ProjectDto createProject(CreateProjectRequest request) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        Checks.requirePermission(principal, "project");
        String stamp = TimeFormats.DISPLAY.format(LocalDateTime.now());
        ProjectDto created = new ProjectDto(
                "prj_" + System.currentTimeMillis(),
                request.name(),
                request.code(),
                "draft",
                principal.displayName(),
                1, 0, stamp,
                request.description() == null ? "" : request.description()
        );
        projects.add(0, created);
        owners.put(created.id(), principal.userId());
        auditRecorder.record("create_project", created.id(), null, null,
                "创建项目 " + created.code(), "success");
        circulationIntake.openTicket("project", created.id(), null, null, "新建项目审核：" + created.name());
        return created;
    }
}
