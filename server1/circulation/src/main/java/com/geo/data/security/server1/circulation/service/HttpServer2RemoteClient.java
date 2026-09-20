package com.geo.data.security.server1.circulation.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import java.util.StringJoiner;

@Component("httpServer2RemoteClient")
@ConditionalOnProperty(prefix = "server2.dispatch", name = "enabled", havingValue = "true")
public class HttpServer2RemoteClient implements Server2RemoteClient {

    private static final Logger log = LoggerFactory.getLogger(HttpServer2RemoteClient.class);

    private final Server2DispatchProperties properties;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public HttpServer2RemoteClient(Server2DispatchProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofMillis(Math.max(1_000, properties.getConnectTimeoutMs())))
                .followRedirects(HttpClient.Redirect.NORMAL)
                .version(HttpClient.Version.HTTP_1_1)
                .build();
    }

    @Override
    public boolean enabled() {
        return properties.isEnabled() && properties.getBaseUrl() != null && !properties.getBaseUrl().isBlank()
                && !serviceToken().isBlank();
    }

    @Override
    public boolean adminEnabled() {
        return enabled() && adminToken() != null && !adminToken().isBlank();
    }

    @Override
    public JsonNode getHealth() {
        return jsonGet("/health", false, false);
    }

    @Override
    public JsonNode getCapabilities() {
        return jsonGet("/internal/capabilities", true, false);
    }

    @Override
    public JsonNode getTask(String taskId) {
        requireEnabled();
        String id = encodePath(taskId);
        JsonNode body = jsonGet("/api/v1/tasks/" + id, true, false);
        if (body.isEmpty()) {
            body = jsonGet("/internal/tasks/" + id, true, false);
        }
        return body;
    }

    @Override
    public JsonNode getIngestSession(String uploadId) {
        return jsonGet("/api/v1/ingest/sessions/" + encodePath(uploadId), true, false);
    }

    @Override
    public JsonNode getVerification(String resultId) {
        String id = encodePath(resultId);
        JsonNode body = jsonGet("/api/v1/results/" + id + "/verification", true, false);
        if (body.isEmpty()) {
            body = jsonGet("/internal/results/" + id + "/verification", true, false);
        }
        return body;
    }

    @Override
    public JsonNode getManifest(String resultId) {
        return jsonGet("/api/v1/results/" + encodePath(resultId) + "/manifest", true, false);
    }

    @Override
    public JsonNode postResultApprove(String resultId, String reviewerId) {
        ObjectNode body = objectMapper.createObjectNode();
        body.put("reviewer_id", reviewerId);
        String id = encodePath(resultId);
        JsonNode response = jsonPost("/api/v1/results/" + id + "/approve", body, true, false);
        if (response.isEmpty()) {
            response = jsonPost("/internal/results/" + id + "/approve", body, true, false);
        }
        return response;
    }

    @Override
    public JsonNode postResultExport(String resultId) {
        return jsonPost("/api/v1/results/" + encodePath(resultId) + "/export", objectMapper.createObjectNode(), true, false);
    }

    @Override
    public byte[] downloadResultExportCompat(String resultId) {
        return bytesGet("/api/v1/results/" + encodePath(resultId) + "/export", true, false);
    }

    @Override
    public JsonNode getExportJob(String exportId) {
        return jsonGet("/api/v1/exports/" + encodePath(exportId), true, false);
    }

    @Override
    public byte[] downloadExportZip(String exportId) {
        return bytesGet("/api/v1/exports/" + encodePath(exportId) + "/download", true, false);
    }

    @Override
    public byte[] downloadResultFile(String resultId, String filename) {
        return bytesGet("/api/v1/results/" + encodePath(resultId) + "/files/" + encodePath(filename), true, false);
    }

    @Override
    public JsonNode provenanceSearch(Map<String, String> query) {
        StringJoiner joiner = new StringJoiner("&");
        if (query != null) {
            for (Map.Entry<String, String> entry : query.entrySet()) {
                if (entry.getValue() == null || entry.getValue().isBlank()) {
                    continue;
                }
                joiner.add(entry.getKey() + "=" + URLEncoder.encode(entry.getValue(), StandardCharsets.UTF_8));
            }
        }
        String qs = joiner.toString();
        String path = qs.isBlank() ? "/api/v1/provenance/search" : "/api/v1/provenance/search?" + qs;
        return jsonGet(path, true, false);
    }

    @Override
    public JsonNode provenanceQuery(String resultId) {
        String encoded = URLEncoder.encode(resultId, StandardCharsets.UTF_8);
        return jsonPost("/api/v1/provenance/query?result_id=" + encoded, objectMapper.createObjectNode(), true, false);
    }

    @Override
    public JsonNode watermarkDetect(JsonNode body) {
        return jsonPost("/api/v1/watermarks/detect", body, true, false);
    }

    @Override
    public JsonNode watermarkVerify(JsonNode body) {
        return jsonPost("/api/v1/watermarks/verify", body, true, false);
    }

    @Override
    public JsonNode internalAuditRetention() {
        return jsonGet("/internal/audit/retention", true, false);
    }

    @Override
    public JsonNode internalTraceVerify() {
        return jsonGet("/internal/trace/verify", true, false);
    }

    @Override
    public JsonNode internalTraceArtifact(String artifactId) {
        return jsonGet("/internal/trace/artifact/" + encodePath(artifactId), true, false);
    }

    @Override
    public JsonNode adminGet(String path) {
        requireAdmin();
        return jsonGet(normalizeAdminPath(path), false, true);
    }

    @Override
    public JsonNode adminPost(String path, JsonNode body) {
        requireAdmin();
        return jsonPost(normalizeAdminPath(path), body == null ? objectMapper.createObjectNode() : body, false, true);
    }

    private static String normalizeAdminPath(String path) {
        if (path == null || path.isBlank()) {
            return "/admin/overview";
        }
        return path.startsWith("/") ? path : "/" + path;
    }

    private JsonNode jsonGet(String path, boolean serviceAuth, boolean adminAuth) {
        requireEnabled();
        try {
            HttpRequest.Builder builder = HttpRequest.newBuilder(uri(path))
                    .timeout(Duration.ofSeconds(60))
                    .GET();
            applyAuth(builder, serviceAuth, adminAuth);
            HttpResponse<String> response = httpClient.send(builder.build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            return parseJsonResponse(response, path);
        } catch (ApiException ex) {
            throw ex;
        } catch (Exception ex) {
            log.warn("server2 GET {} failed", path, ex);
            throw new ApiException(ErrorCode.SERVICE_UNAVAILABLE, "服务器2请求失败：" + path);
        }
    }

    private JsonNode jsonPost(String path, JsonNode body, boolean serviceAuth, boolean adminAuth) {
        requireEnabled();
        try {
            HttpRequest.Builder builder = HttpRequest.newBuilder(uri(path))
                    .timeout(Duration.ofSeconds(120))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(body)));
            applyAuth(builder, serviceAuth, adminAuth);
            HttpResponse<String> response = httpClient.send(builder.build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            return parseJsonResponse(response, path);
        } catch (ApiException ex) {
            throw ex;
        } catch (Exception ex) {
            log.warn("server2 POST {} failed", path, ex);
            throw new ApiException(ErrorCode.SERVICE_UNAVAILABLE, "服务器2请求失败：" + path);
        }
    }

    private byte[] bytesGet(String path, boolean serviceAuth, boolean adminAuth) {
        requireEnabled();
        try {
            HttpRequest.Builder builder = HttpRequest.newBuilder(uri(path))
                    .timeout(Duration.ofMinutes(30))
                    .GET();
            applyAuth(builder, serviceAuth, adminAuth);
            HttpResponse<byte[]> response = httpClient.send(builder.build(), HttpResponse.BodyHandlers.ofByteArray());
            int status = response.statusCode();
            if (status >= 200 && status < 300) {
                return response.body();
            }
            String snippet = response.body() == null ? "" : new String(response.body(), 0, Math.min(500, response.body().length), StandardCharsets.UTF_8);
            log.warn("server2 download {} status={} body={}", path, status, snippet);
            throw new ApiException(ErrorCode.BAD_REQUEST, "服务器2下载失败：" + status);
        } catch (ApiException ex) {
            throw ex;
        } catch (Exception ex) {
            log.warn("server2 download {} failed", path, ex);
            throw new ApiException(ErrorCode.SERVICE_UNAVAILABLE, "服务器2下载失败");
        }
    }

    private JsonNode parseJsonResponse(HttpResponse<String> response, String path) throws IOException {
        int status = response.statusCode();
        String body = response.body() == null ? "" : response.body();
        if (status >= 200 && status < 300) {
            if (body.isBlank()) {
                return objectMapper.createObjectNode();
            }
            return objectMapper.readTree(body);
        }
        log.warn("server2 {} status={} body={}", path, status, body.length() > 800 ? body.substring(0, 800) : body);
        if (status == 401 || status == 403) {
            throw new ApiException(ErrorCode.UNAUTHORIZED, "服务器2认证失败");
        }
        if (status == 404) {
            return objectMapper.createObjectNode();
        }
        String detail = body.length() > 200 ? body.substring(0, 200) : body;
        throw new ApiException(ErrorCode.BAD_REQUEST, "服务器2拒绝请求：" + detail);
    }

    private void applyAuth(HttpRequest.Builder builder, boolean serviceAuth, boolean adminAuth) {
        if (adminAuth) {
            builder.header("X-Admin-Token", adminToken());
        } else if (serviceAuth) {
            builder.header("X-Service-Token", serviceToken());
        }
    }

    private void requireEnabled() {
        if (!enabled()) {
            throw new ApiException(ErrorCode.SERVICE_UNAVAILABLE, "未配置服务器2服务令牌");
        }
    }

    private void requireAdmin() {
        if (!adminEnabled()) {
            throw new ApiException(ErrorCode.SERVICE_UNAVAILABLE, "未配置服务器2管理员令牌");
        }
    }

    private URI uri(String path) {
        String base = properties.getBaseUrl().replaceAll("/+$", "");
        return URI.create(base + path);
    }

    private String serviceToken() {
        return properties.getToken() == null ? "" : properties.getToken().trim();
    }

    private String adminToken() {
        return properties.getAdminToken() == null ? "" : properties.getAdminToken().trim();
    }

    private static String encodePath(String segment) {
        return URLEncoder.encode(segment, StandardCharsets.UTF_8).replace("+", "%20");
    }
}
