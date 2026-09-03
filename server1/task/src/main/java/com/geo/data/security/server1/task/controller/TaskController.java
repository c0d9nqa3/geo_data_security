package com.geo.data.security.server1.task.controller;

import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiResponse;
import com.geo.data.security.server1.task.service.TaskService;
import com.geo.data.security.server1.task.controller.dto.CreateTaskRequest;
import com.geo.data.security.server1.task.controller.dto.TaskDto;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/tasks")
public class TaskController {

    private final TaskService taskService;

    public TaskController(TaskService taskService) {
        this.taskService = taskService;
    }

    @GetMapping
    public ApiResponse<List<TaskDto>> list(
            @RequestParam(value = "projectId", required = false) String projectId) {
        return ApiResponse.ok(RequestContext.requestId(), taskService.listTasks(projectId));
    }

    @PostMapping
    public ApiResponse<TaskDto> create(@Valid @RequestBody CreateTaskRequest request) {
        return ApiResponse.ok(RequestContext.requestId(), taskService.createTask(request));
    }
}
