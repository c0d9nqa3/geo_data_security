package com.geo.data.security.server1.ingest.controller.dto;

public record FileProvenanceEvidenceDto(
        String taskId,
        String resultId,
        String sourcePath,
        String sourceHash,
        String outputHash,
        String chainTx,
        String chainBlock,
        Boolean onChain,
        Boolean verified,
        String method,
        Integer filesProcessed,
        Integer matched,
        String watermark,
        String server2Status
) {
}
