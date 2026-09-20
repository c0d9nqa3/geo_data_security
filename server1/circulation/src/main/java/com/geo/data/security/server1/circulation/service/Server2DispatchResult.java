package com.geo.data.security.server1.circulation.service;

public record Server2DispatchResult(
        String sourcePath,
        String taskId,
        String status,
        String resultId,
        String dataType,
        String classification,
        String watermark
) {
}
