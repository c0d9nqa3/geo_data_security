package com.geo.data.security.server1.task.controller;

import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiResponse;
import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.task.controller.dto.CreateTaskRequest;
import com.geo.data.security.server1.task.controller.dto.TaskDto;
import com.geo.data.security.server1.task.controller.dto.TaskResultDto;
import com.geo.data.security.server1.task.service.TaskService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/tasks")
public class TaskController {

    private final TaskService taskService;

    public TaskController(TaskService taskService) {
        this.taskService = taskService;
    }

    @GetMapping
    public ApiResponse<PageDto<TaskDto>> list(
            @RequestParam(value = "projectId", required = false) String projectId,
            @RequestParam(value = "applyType", required = false) String applyType,
            @RequestParam(value = "status", required = false) String status,
            @RequestParam(value = "page", required = false) Integer page,
            @RequestParam(value = "pageSize", required = false) Integer pageSize) {
        return ApiResponse.ok(RequestContext.requestId(),
                taskService.listTasks(projectId, applyType, status, page, pageSize));
    }

    @GetMapping("/{taskId}")
    public ApiResponse<TaskDto> get(@PathVariable String taskId) {
        return ApiResponse.ok(RequestContext.requestId(), taskService.getTask(taskId));
    }

    @PostMapping("/{taskId}/urge")
    public ApiResponse<TaskDto> urge(@PathVariable String taskId) {
        return ApiResponse.ok(RequestContext.requestId(), taskService.urge(taskId));
    }

    @PostMapping("/{taskId}/retry")
    public ApiResponse<TaskDto> retry(@PathVariable String taskId) {
        return ApiResponse.ok(RequestContext.requestId(), taskService.retry(taskId));
    }

    @PostMapping("/{taskId}/withdraw")
    public ApiResponse<TaskDto> withdraw(@PathVariable String taskId) {
        return ApiResponse.ok(RequestContext.requestId(), taskService.withdraw(taskId));
    }

    @PostMapping("/{taskId}/delete")
    public ApiResponse<TaskDto> delete(@PathVariable String taskId) {
        return ApiResponse.ok(RequestContext.requestId(), taskService.deleteTask(taskId));
    }

    @PostMapping
    public ApiResponse<TaskDto> create(@Valid @RequestBody CreateTaskRequest request) {
        return ApiResponse.ok(RequestContext.requestId(), taskService.createTask(request));
    }

    @PostMapping("/{taskId}/sync")
    public ApiResponse<TaskDto> sync(@PathVariable String taskId) {
        return ApiResponse.ok(RequestContext.requestId(), taskService.syncFromServer2(taskId));
    }

    @PostMapping("/{taskId}/submit-review")
    public ApiResponse<TaskDto> submitReview(@PathVariable String taskId) {
        return ApiResponse.ok(RequestContext.requestId(), taskService.submitForReview(taskId));
    }

    @PostMapping("/{taskId}/cancel")
    public ApiResponse<TaskDto> cancel(@PathVariable String taskId) {
        return ApiResponse.ok(RequestContext.requestId(), taskService.cancelTask(taskId));
    }

    @PostMapping("/{taskId}/download")
    public ApiResponse<TaskResultDto> download(@PathVariable String taskId) {
        return ApiResponse.ok(RequestContext.requestId(), taskService.downloadResult(taskId));
    }
}
