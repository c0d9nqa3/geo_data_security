package com.geo.data.security.server1.ingest.controller.dto;

public record FileProvenanceNodeDto(
        String key,
        String label,
        String state,
        String actor,
        String time,
        String remark
) {
}
