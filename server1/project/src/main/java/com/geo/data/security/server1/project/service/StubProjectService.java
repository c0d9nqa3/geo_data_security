package com.geo.data.security.server1.project.service;

import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.circulation.service.CirculationIntake;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.project.controller.dto.CreateProjectRequest;
import com.geo.data.security.server1.project.controller.dto.ProjectDto;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "stub")
public class StubProjectService implements ProjectService {

    private final List<ProjectDto> projects = new CopyOnWriteArrayList<>(List.of(
            new ProjectDto("prj_1001", "城区正射影像库", "DOM-2026-01", "active", "张工", 5, 12,
                    "2026-09-01 16:20", "城区正射影像采集与水印处理项目")
    ));
    private final AuditRecorder auditRecorder;
    private final CirculationIntake circulationIntake;

    public StubProjectService(AuditRecorder auditRecorder, CirculationIntake circulationIntake) {
        this.auditRecorder = auditRecorder;
        this.circulationIntake = circulationIntake;
    }

    @Override
    public List<ProjectDto> listProjects() {
        RequestContext.requirePrincipal();
        return new ArrayList<>(projects);
    }

    @Override
    public ProjectDto createProject(CreateProjectRequest request) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
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
        auditRecorder.record("create_project", created.id(), null, null,
                "创建项目 " + created.code(), "success");
        circulationIntake.openTicket("project", created.id(), null, null, "新建项目审核：" + created.name());
        return created;
    }
}
