package com.geo.data.security.server1.ingest.controller.dto;

import java.util.List;

public record FileProvenanceDto(
        String fileId,
        String fileName,
        String projectId,
        String projectName,
        String fileStatus,
        String currentKey,
        String currentLabel,
        boolean liveFromServer2,
        String liveHint,
        List<FileProvenanceNodeDto> nodes,
        FileProvenanceEvidenceDto evidence
) {
}
