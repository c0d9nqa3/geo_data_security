package com.geo.data.security.server1.task.controller.dto;

public record TaskNodeDto(
        String key,
        String label,
        String state,
        String actor,
        String time,
        String remark
) {
}
