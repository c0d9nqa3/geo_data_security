package com.geo.data.security.server1.task.service;

import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.circulation.service.CirculationIntake;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.task.controller.dto.CreateTaskRequest;
import com.geo.data.security.server1.task.controller.dto.TaskDto;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "stub")
public class StubTaskService implements TaskService {

    private final List<TaskDto> tasks = new CopyOnWriteArrayList<>(List.of(
            new TaskDto("task_3001", "prj_1001", "城区正射影像库", "file_2001", "tile_A12.tif",
                    "GeoTIFF 水印", "waiting_review", 100, "张工", "2026-09-01 15:30", "2026-09-01 16:05")
    ));
    private final AuditRecorder auditRecorder;
    private final CirculationIntake circulationIntake;

    public StubTaskService(AuditRecorder auditRecorder, CirculationIntake circulationIntake) {
        this.auditRecorder = auditRecorder;
        this.circulationIntake = circulationIntake;
    }

    @Override
    public List<TaskDto> listTasks(String projectId) {
        RequestContext.requirePrincipal();
        if (projectId == null || projectId.isBlank()) {
            return new ArrayList<>(tasks);
        }
        return tasks.stream().filter(t -> projectId.equals(t.projectId())).toList();
    }

    @Override
    public TaskDto createTask(CreateTaskRequest request) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        if (request.fileId() == null || request.fileId().isBlank()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "请选择关联文件");
        }
        String stamp = TimeFormats.DISPLAY.format(LocalDateTime.now());
        TaskDto created = new TaskDto(
                "task_" + System.currentTimeMillis(),
                "prj_1001", "城区正射影像库", request.fileId(), request.fileId(),
                request.type(), "waiting_review", 0, principal.displayName(), stamp, stamp
        );
        tasks.add(0, created);
        auditRecorder.record("submit_task", created.projectId(), created.fileId(), created.id(),
                "提交任务 " + created.id(), "success");
        circulationIntake.openTicket("task", created.projectId(), created.fileId(), created.id(),
                "提交任务审核：" + created.type());
        return created;
    }
}
