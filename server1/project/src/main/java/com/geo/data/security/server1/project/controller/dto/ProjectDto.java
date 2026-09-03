package com.geo.data.security.server1.project.controller.dto;

public record ProjectDto(
        String id,
        String name,
        String code,
        String status,
        String owner,
        int memberCount,
        int fileCount,
        String updatedAt,
        String description
) {
}
