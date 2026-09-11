package com.geo.data.security.server1.app.dashboard;

import com.geo.data.security.server1.audit.controller.dto.AuditEventDto;
import com.geo.data.security.server1.task.controller.dto.TaskDto;

import java.util.List;

public record DashboardOverviewDto(
        long projectCount,
        long fileCount,
        long runningTaskCount,
        long alertCount,
        List<TaskDto> recentTasks,
        List<AuditEventDto> recentAudits,
        List<DashboardTrendPoint> taskTrend,
        List<DashboardTrendPoint> auditTrend
) {
}
