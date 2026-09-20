package com.geo.data.security.server1.circulation.service;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.Map;

/** Server2 控制面 API（文档 v2026-09-19），由服务器1代持 X-Service-Token / X-Admin-Token。 */
public interface Server2RemoteClient {

    boolean enabled();

    boolean adminEnabled();

    JsonNode getHealth();

    JsonNode getCapabilities();

    JsonNode getTask(String taskId);

    JsonNode getIngestSession(String uploadId);

    JsonNode getVerification(String resultId);

    JsonNode getManifest(String resultId);

    JsonNode postResultApprove(String resultId, String reviewerId);

    JsonNode postResultExport(String resultId);

    byte[] downloadResultExportCompat(String resultId);

    JsonNode getExportJob(String exportId);

    byte[] downloadExportZip(String exportId);

    byte[] downloadResultFile(String resultId, String filename);

    JsonNode provenanceSearch(Map<String, String> query);

    JsonNode provenanceQuery(String resultId);

    JsonNode watermarkDetect(JsonNode body);

    JsonNode watermarkVerify(JsonNode body);

    JsonNode internalAuditRetention();

    JsonNode internalTraceVerify();

    JsonNode internalTraceArtifact(String artifactId);

    JsonNode adminGet(String path);

    JsonNode adminPost(String path, JsonNode body);
}
