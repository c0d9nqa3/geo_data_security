package com.geo.data.security.server1.app.dashboard;

import com.geo.data.security.server1.audit.controller.dto.AuditEventDto;
import com.geo.data.security.server1.audit.service.AuditQueryService;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiResponse;
import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.ingest.service.FileIngestService;
import com.geo.data.security.server1.project.service.ProjectService;
import com.geo.data.security.server1.task.controller.dto.TaskDto;
import com.geo.data.security.server1.task.service.TaskService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/dashboard")
public class DashboardController {

    private static final ZoneId ZONE = ZoneId.of("Asia/Shanghai");

    private final ProjectService projectService;
    private final FileIngestService fileIngestService;
    private final TaskService taskService;
    private final AuditQueryService auditQueryService;

    public DashboardController(ProjectService projectService, FileIngestService fileIngestService,
                               TaskService taskService, AuditQueryService auditQueryService) {
        this.projectService = projectService;
        this.fileIngestService = fileIngestService;
        this.taskService = taskService;
        this.auditQueryService = auditQueryService;
    }

    @GetMapping("/overview")
    public ApiResponse<DashboardOverviewDto> overview() {
        RequestContext.requirePrincipal();
        LocalDate from = LocalDate.now(ZONE).minusDays(6);
        List<TaskDto> recentTasks = taskService.listRecentAll(8);
        PageDto<AuditEventDto> audits = auditQueryService.listEvents(null, null, 1, 8);
        PageDto<AuditEventDto> denied = auditQueryService.listEvents(null, "denied", 1, 1);
        PageDto<AuditEventDto> errors = auditQueryService.listEvents(null, "error", 1, 1);
        return ApiResponse.ok(RequestContext.requestId(), new DashboardOverviewDto(
                projectService.countAll(),
                fileIngestService.countAll(),
                taskService.countRunning(),
                denied.total() + errors.total(),
                recentTasks,
                audits.items(),
                fillTrend(taskService.countCreatedByDay(from), from),
                fillTrend(auditQueryService.countByDay(from), from)
        ));
    }

    private static List<DashboardTrendPoint> fillTrend(Map<String, Long> counts, LocalDate from) {
        List<DashboardTrendPoint> points = new ArrayList<>();
        for (int i = 0; i < 7; i++) {
            LocalDate day = from.plusDays(i);
            points.add(new DashboardTrendPoint(day.toString(), counts.getOrDefault(day.toString(), 0L)));
        }
        return points;
    }
}
