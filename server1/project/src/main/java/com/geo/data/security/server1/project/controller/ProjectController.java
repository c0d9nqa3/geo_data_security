package com.geo.data.security.server1.project.controller;

import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiResponse;
import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.project.service.ProjectService;
import com.geo.data.security.server1.project.controller.dto.CreateProjectRequest;
import com.geo.data.security.server1.project.controller.dto.ProjectDto;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/projects")
public class ProjectController {

    private final ProjectService projectService;

    public ProjectController(ProjectService projectService) {
        this.projectService = projectService;
    }

    @GetMapping
    public ApiResponse<PageDto<ProjectDto>> list(
            @RequestParam(value = "keyword", required = false) String keyword,
            @RequestParam(value = "page", required = false) Integer page,
            @RequestParam(value = "pageSize", required = false) Integer pageSize) {
        return ApiResponse.ok(RequestContext.requestId(),
                projectService.listProjects(keyword, page, pageSize));
    }

    @PostMapping
    public ApiResponse<ProjectDto> create(@Valid @RequestBody CreateProjectRequest request) {
        return ApiResponse.ok(RequestContext.requestId(), projectService.createProject(request));
    }
}
