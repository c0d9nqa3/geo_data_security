package com.geo.data.security.server1.circulation.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.geo.data.security.server1.circulation.service.Server2RemoteClient;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ApiResponse;
import com.geo.data.security.server1.common.error.ErrorCode;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 服务器2 文档 API 的增量代理（/api/gds，避免 URL 含 server2 被网关拦截）。
 * 不改变原有 /api/files、/api/circulations 等接口行为。
 */
@RestController
@RequestMapping("/api/gds")
public class GdsPlatformController {

    private final Server2RemoteClient remote;
    private final ObjectProvider<JdbcTemplate> jdbcProvider;
    private final ObjectMapper objectMapper;

    public GdsPlatformController(
            Server2RemoteClient remote, ObjectProvider<JdbcTemplate> jdbcProvider, ObjectMapper objectMapper) {
        this.remote = remote;
        this.jdbcProvider = jdbcProvider;
        this.objectMapper = objectMapper;
    }

    @GetMapping("/health")
    public ApiResponse<JsonNode> health() {
        return ok(remote.getHealth());
    }

    @GetMapping("/capabilities")
    public ApiResponse<JsonNode> capabilities() {
        ensureRemote();
        return ok(remote.getCapabilities());
    }

    @GetMapping("/tasks/{taskId}")
    public ApiResponse<JsonNode> task(@PathVariable String taskId) {
        ensureRemote();
        return ok(remote.getTask(taskId));
    }

    @GetMapping("/ingest/sessions/{uploadId}")
    public ApiResponse<JsonNode> ingestSession(@PathVariable String uploadId) {
        ensureRemote();
        return ok(remote.getIngestSession(uploadId));
    }

    @GetMapping("/results/{resultId}/verification")
    public ApiResponse<JsonNode> verification(@PathVariable String resultId) {
        ensureRemote();
        return ok(remote.getVerification(resultId));
    }

    @GetMapping("/results/{resultId}/manifest")
    public ApiResponse<JsonNode> manifest(@PathVariable String resultId) {
        ensureRemote();
        return ok(remote.getManifest(resultId));
    }

    @PostMapping("/results/{resultId}/approve")
    public ApiResponse<JsonNode> approve(@PathVariable String resultId) {
        ensureRemote();
        var principal = RequestContext.principal();
        String reviewer = principal == null || principal.userId() == null ? "server1-service" : principal.userId();
        return ok(remote.postResultApprove(resultId, reviewer));
    }

    @PostMapping("/results/{resultId}/export")
    public ApiResponse<JsonNode> startExport(@PathVariable String resultId) {
        ensureRemote();
        return ok(remote.postResultExport(resultId));
    }

    @GetMapping("/results/{resultId}/export")
    public ResponseEntity<byte[]> exportCompat(@PathVariable String resultId) {
        ensureRemote();
        byte[] body = remote.downloadResultExportCompat(resultId);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + resultId + "-export.zip\"")
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .body(body);
    }

    @GetMapping("/exports/{exportId}")
    public ApiResponse<JsonNode> exportJob(@PathVariable String exportId) {
        ensureRemote();
        return ok(remote.getExportJob(exportId));
    }

    @GetMapping("/exports/{exportId}/download")
    public ResponseEntity<byte[]> downloadExport(@PathVariable String exportId) {
        ensureRemote();
        byte[] zip = remote.downloadExportZip(exportId);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + exportId + ".zip\"")
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .body(zip);
    }

    @GetMapping("/results/{resultId}/files/{filename}")
    public ResponseEntity<byte[]> downloadFile(@PathVariable String resultId, @PathVariable String filename) {
        ensureRemote();
        byte[] body = remote.downloadResultFile(resultId, filename);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .body(body);
    }

    @GetMapping("/provenance/search")
    public ApiResponse<JsonNode> provenanceSearch(
            @RequestParam(required = false) String projectId,
            @RequestParam(required = false) String artifactId,
            @RequestParam(required = false) String classification,
            @RequestParam(required = false) String inputHash) {
        ensureRemote();
        Map<String, String> query = new LinkedHashMap<>();
        if (projectId != null) {
            query.put("project_id", projectId);
        }
        if (artifactId != null) {
            query.put("artifact_id", artifactId);
        }
        if (classification != null) {
            query.put("classification", classification);
        }
        if (inputHash != null) {
            query.put("input_hash", inputHash);
        }
        return ok(remote.provenanceSearch(query));
    }

    @PostMapping("/provenance/query")
    public ApiResponse<JsonNode> provenanceQuery(@RequestParam("resultId") String resultId) {
        ensureRemote();
        return ok(remote.provenanceQuery(resultId));
    }

    @PostMapping("/watermarks/detect")
    public ApiResponse<JsonNode> watermarkDetect(@RequestBody JsonNode body) {
        ensureRemote();
        return ok(remote.watermarkDetect(body));
    }

    @PostMapping("/watermarks/verify")
    public ApiResponse<JsonNode> watermarkVerify(@RequestBody JsonNode body) {
        ensureRemote();
        return ok(remote.watermarkVerify(body));
    }

    @GetMapping("/internal/audit-retention")
    public ApiResponse<JsonNode> auditRetention() {
        ensureRemote();
        return ok(remote.internalAuditRetention());
    }

    @GetMapping("/internal/trace/verify")
    public ApiResponse<JsonNode> traceVerify() {
        ensureRemote();
        return ok(remote.internalTraceVerify());
    }

    @GetMapping("/internal/trace/artifacts/{artifactId}")
    public ApiResponse<JsonNode> traceArtifact(@PathVariable String artifactId) {
        ensureRemote();
        return ok(remote.internalTraceArtifact(artifactId));
    }

    @GetMapping("/files/{fileId}/context")
    public ApiResponse<JsonNode> fileContext(@PathVariable String fileId) {
        FileRefs refs = loadFileRefs(fileId);
        ObjectNode out = objectMapper.createObjectNode();
        out.put("fileId", refs.fileId());
        out.put("fileName", refs.fileName());
        out.put("projectId", refs.projectId());
        out.put("server2TaskId", refs.taskId());
        out.put("server2ResultId", refs.resultId());
        out.put("server2SourcePath", refs.sourcePath());
        return ok(out);
    }

    @GetMapping("/files/{fileId}/verification")
    public ApiResponse<JsonNode> fileVerification(@PathVariable String fileId) {
        String resultId = requireResultId(fileId);
        ensureRemote();
        return ok(remote.getVerification(resultId));
    }

    @GetMapping("/files/{fileId}/manifest")
    public ApiResponse<JsonNode> fileManifest(@PathVariable String fileId) {
        String resultId = requireResultId(fileId);
        ensureRemote();
        return ok(remote.getManifest(resultId));
    }

    @PostMapping("/files/{fileId}/export")
    public ApiResponse<JsonNode> fileStartExport(@PathVariable String fileId) {
        String resultId = requireResultId(fileId);
        ensureRemote();
        return ok(remote.postResultExport(resultId));
    }

    @PostMapping("/files/{fileId}/provenance/query")
    public ApiResponse<JsonNode> fileProvenanceQuery(@PathVariable String fileId) {
        String resultId = requireResultId(fileId);
        ensureRemote();
        return ok(remote.provenanceQuery(resultId));
    }

    @GetMapping("/admin/overview")
    public ApiResponse<JsonNode> adminOverview() {
        ensureAdmin();
        return ok(remote.adminGet("/admin/overview"));
    }

    @GetMapping("/admin/storage")
    public ApiResponse<JsonNode> adminStorage() {
        ensureAdmin();
        return ok(remote.adminGet("/admin/storage"));
    }

    @GetMapping("/admin/database/{table}")
    public ApiResponse<JsonNode> adminDatabase(
            @PathVariable String table,
            @RequestParam(defaultValue = "20") int limit,
            @RequestParam(defaultValue = "0") int offset) {
        ensureAdmin();
        return ok(remote.adminGet("/admin/database/" + table + "?limit=" + limit + "&offset=" + offset));
    }

    @GetMapping("/admin/trace/chain")
    public ApiResponse<JsonNode> adminTraceChain() {
        ensureAdmin();
        return ok(remote.adminGet("/admin/trace/chain"));
    }

    @GetMapping("/admin/audit")
    public ApiResponse<JsonNode> adminAudit() {
        ensureAdmin();
        return ok(remote.adminGet("/admin/audit"));
    }

    @GetMapping("/admin/besu")
    public ApiResponse<JsonNode> adminBesu() {
        ensureAdmin();
        return ok(remote.adminGet("/admin/besu"));
    }

    @GetMapping("/admin/relationship")
    public ApiResponse<JsonNode> adminRelationship() {
        ensureAdmin();
        return ok(remote.adminGet("/admin/relationship"));
    }

    private ApiResponse<JsonNode> ok(JsonNode data) {
        return ApiResponse.ok(RequestContext.requestId(), data);
    }

    private void ensureRemote() {
        if (!remote.enabled()) {
            throw new ApiException(ErrorCode.SERVICE_UNAVAILABLE, "未配置服务器2服务令牌");
        }
    }

    private void ensureAdmin() {
        if (!remote.adminEnabled()) {
            throw new ApiException(ErrorCode.SERVICE_UNAVAILABLE, "未配置服务器2管理员令牌 GDS_SERVER2_ADMIN_TOKEN");
        }
    }

    private String requireResultId(String fileId) {
        FileRefs refs = loadFileRefs(fileId);
        if (refs.resultId() == null || refs.resultId().isBlank()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "该文件尚无服务器2结果 ID，请先完成分发处理");
        }
        return refs.resultId();
    }

    private FileRefs loadFileRefs(String fileId) {
        JdbcTemplate jdbc = jdbcProvider.getIfAvailable();
        if (jdbc == null) {
            throw new ApiException(ErrorCode.SERVICE_UNAVAILABLE, "当前环境未启用数据库，无法按文件 ID 解析服务器2上下文");
        }
        List<FileRefs> rows = jdbc.query(
                """
                        SELECT f.file_id, f.file_name, f.project_id,
                               COALESCE(NULLIF(f.server2_result_id,''), c.result_id, '') AS result_id,
                               COALESCE(f.server2_task_id, '') AS task_id,
                               COALESCE(f.server2_source_path, '') AS source_path
                        FROM biz_file f
                        LEFT JOIN biz_circulation c ON c.file_id = f.file_id AND c.deleted = 0
                        WHERE f.file_id = ?
                        ORDER BY c.id DESC
                        LIMIT 1
                        """,
                (rs, rowNum) -> new FileRefs(
                        rs.getString("file_id"),
                        rs.getString("file_name"),
                        rs.getString("project_id"),
                        rs.getString("result_id"),
                        rs.getString("task_id"),
                        rs.getString("source_path")),
                fileId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.NOT_FOUND, "文件不存在");
        }
        return rows.get(0);
    }

    private record FileRefs(String fileId, String fileName, String projectId, String resultId, String taskId, String sourcePath) {
    }
}
