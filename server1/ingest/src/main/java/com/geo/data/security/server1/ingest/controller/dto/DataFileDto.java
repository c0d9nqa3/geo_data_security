package com.geo.data.security.server1.ingest.controller.dto;

public record DataFileDto(
        String id,
        String projectId,
        String projectName,
        String name,
        String kind,
        double sizeMb,
        String status,
        String hash,
        String uploadedBy,
        String uploadedAt
) {
}
