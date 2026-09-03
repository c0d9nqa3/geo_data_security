package com.geo.data.security.server1.project.service;

import com.geo.data.security.server1.project.controller.dto.CreateProjectRequest;
import com.geo.data.security.server1.project.controller.dto.ProjectDto;

import java.util.List;

public interface ProjectService {

    List<ProjectDto> listProjects();

    ProjectDto createProject(CreateProjectRequest request);
}
