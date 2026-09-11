package com.geo.data.security.server1.task.service;

import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.task.controller.dto.CreateTaskRequest;
import com.geo.data.security.server1.task.controller.dto.TaskDto;
import com.geo.data.security.server1.task.controller.dto.TaskResultDto;

public interface TaskService {

    PageDto<TaskDto> listTasks(String projectId, String applyType, String status, Integer page, Integer pageSize);

    long countRunning();

    java.util.List<TaskDto> listRecentAll(int limit);

    java.util.Map<String, Long> countCreatedByDay(java.time.LocalDate fromInclusive);

    TaskDto getTask(String taskId);

    TaskDto urge(String taskId);

    TaskDto retry(String taskId);

    TaskDto withdraw(String taskId);

    TaskDto deleteTask(String taskId);

    TaskDto createTask(CreateTaskRequest request);

    TaskDto syncFromServer2(String taskId);

    TaskDto submitForReview(String taskId);

    TaskDto cancelTask(String taskId);

    TaskResultDto downloadResult(String taskId);
}
