package com.geo.data.security.server1.circulation.service;

public record Server2TraceSnapshot(
        boolean available,
        String hint,
        String taskId,
        String resultId,
        String taskStatus,
        String resultStatus,
        String sourcePath,
        String sourceHash,
        String outputHash,
        String watermark,
        Boolean verified,
        String method,
        Integer filesProcessed,
        Integer matched,
        Boolean onChain,
        String chainTx,
        String chainBlock,
        String processedAt
) {
    public static Server2TraceSnapshot unavailable(String hint) {
        return new Server2TraceSnapshot(
                false, hint == null ? "" : hint,
                "", "", "", "", "", "", "", "",
                null, "", null, null, null, "", "", "");
    }
}
