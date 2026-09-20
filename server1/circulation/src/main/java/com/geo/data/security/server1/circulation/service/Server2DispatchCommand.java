package com.geo.data.security.server1.circulation.service;

import java.nio.file.Path;

public record Server2DispatchCommand(
        String projectId,
        String fileId,
        String fileName,
        String dataKind,
        String contentHash,
        Path localFile,
        String userId,
        String reviewerId
) {
}
