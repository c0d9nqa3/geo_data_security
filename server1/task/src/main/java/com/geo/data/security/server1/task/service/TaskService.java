package com.geo.data.security.server1.task.service;

import com.geo.data.security.server1.task.controller.dto.CreateTaskRequest;
import com.geo.data.security.server1.task.controller.dto.TaskDto;

import java.util.List;

public interface TaskService {

    List<TaskDto> listTasks(String projectId);

    TaskDto createTask(CreateTaskRequest request);
}
