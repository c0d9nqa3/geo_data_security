package com.geo.data.security.server1.circulation.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
@ConditionalOnMissingBean(name = "httpServer2RemoteClient")
public class NoopServer2RemoteClient implements Server2RemoteClient {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public boolean enabled() {
        return false;
    }

    @Override
    public boolean adminEnabled() {
        return false;
    }

    private JsonNode empty() {
        return objectMapper.createObjectNode();
    }

    @Override
    public JsonNode getHealth() {
        return empty();
    }

    @Override
    public JsonNode getCapabilities() {
        return empty();
    }

    @Override
    public JsonNode getTask(String taskId) {
        return empty();
    }

    @Override
    public JsonNode getIngestSession(String uploadId) {
        return empty();
    }

    @Override
    public JsonNode getVerification(String resultId) {
        return empty();
    }

    @Override
    public JsonNode getManifest(String resultId) {
        return empty();
    }

    @Override
    public JsonNode postResultApprove(String resultId, String reviewerId) {
        return empty();
    }

    @Override
    public JsonNode postResultExport(String resultId) {
        return empty();
    }

    @Override
    public byte[] downloadResultExportCompat(String resultId) {
        return new byte[0];
    }

    @Override
    public JsonNode getExportJob(String exportId) {
        return empty();
    }

    @Override
    public byte[] downloadExportZip(String exportId) {
        return new byte[0];
    }

    @Override
    public byte[] downloadResultFile(String resultId, String filename) {
        return new byte[0];
    }

    @Override
    public JsonNode provenanceSearch(Map<String, String> query) {
        return empty();
    }

    @Override
    public JsonNode provenanceQuery(String resultId) {
        return empty();
    }

    @Override
    public JsonNode watermarkDetect(JsonNode body) {
        return empty();
    }

    @Override
    public JsonNode watermarkVerify(JsonNode body) {
        return empty();
    }

    @Override
    public JsonNode internalAuditRetention() {
        return empty();
    }

    @Override
    public JsonNode internalTraceVerify() {
        return empty();
    }

    @Override
    public JsonNode internalTraceArtifact(String artifactId) {
        return empty();
    }

    @Override
    public JsonNode adminGet(String path) {
        return empty();
    }

    @Override
    public JsonNode adminPost(String path, JsonNode body) {
        return empty();
    }
}
