package com.geo.data.security.server1.project.service;

import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.project.controller.dto.CreateProjectRequest;
import com.geo.data.security.server1.project.controller.dto.ProjectDto;

public interface ProjectService {

    PageDto<ProjectDto> listProjects(String keyword, Integer page, Integer pageSize);

    long countAll();

    ProjectDto createProject(CreateProjectRequest request);
}
