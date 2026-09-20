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

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.net.URLEncoder;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.atomic.AtomicInteger;

@Component
@ConditionalOnProperty(prefix = "server2.dispatch", name = "enabled", havingValue = "true")
public class HttpServer2DispatchClient implements Server2DispatchClient {

    private static final Logger log = LoggerFactory.getLogger(HttpServer2DispatchClient.class);
    private static final int MAX_CHUNK_SIZE_BYTES = 64 * 1024 * 1024;

    private final Server2DispatchProperties properties;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;
    private final ExecutorService chunkExecutor;

    public HttpServer2DispatchClient(Server2DispatchProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
        int concurrency = chunkConcurrency();
        ThreadFactory threads = new ThreadFactory() {
            private final AtomicInteger seq = new AtomicInteger();

            @Override
            public Thread newThread(Runnable runnable) {
                Thread thread = new Thread(runnable, "server2-chunk-" + seq.incrementAndGet());
                thread.setDaemon(true);
                return thread;
            }
        };
        this.chunkExecutor = Executors.newFixedThreadPool(concurrency, threads);
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofMillis(Math.max(1_000, properties.getConnectTimeoutMs())))
                .followRedirects(HttpClient.Redirect.NORMAL)
                .version(HttpClient.Version.HTTP_1_1)
                .build();
    }

    @Override
    public boolean enabled() {
        return properties.isEnabled() && properties.getBaseUrl() != null && !properties.getBaseUrl().isBlank();
    }

    @Override
    public Server2DispatchResult dispatch(Server2DispatchCommand command) {
        if (command == null || command.localFile() == null || !Files.isRegularFile(command.localFile())) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "分发失败：服务器1本地文件不存在");
        }
        if (token().isBlank()) {
            throw new ApiException(ErrorCode.SERVICE_UNAVAILABLE, "分发失败：未配置服务器2服务令牌");
        }
        Server2KindMapper.Mapping mapping = Server2KindMapper.map(command.dataKind(), command.fileName());
        String watermark = Server2KindMapper.watermark(mapping.dataType(), command.projectId());
        String sha256 = resolveSha256(command);
        try {
            health();
            Ingress ingress = upload(command, mapping, sha256);
            JsonNode task = submitTask(command, mapping, watermark, ingress);
            String taskId = text(task, "task_id");
            JsonNode done = awaitTask(taskId, task);
            String status = text(done, "status").toUpperCase(Locale.ROOT);
            if ("FAILED".equals(status) || "ERROR".equals(status)) {
                String reason = first(done, "error", "detail", "message");
                log.warn("server2 processing failed fileId={} taskId={} body={}", command.fileId(), taskId, done);
                throw new ApiException(ErrorCode.BAD_REQUEST,
                        reason.isBlank() ? "服务器2处理失败" : "服务器2处理失败：" + reason);
            }
            String resultId = text(done, "result_id");
            if (!resultId.isBlank()) {
                approve(resultId, command.reviewerId() == null || command.reviewerId().isBlank()
                        ? "server1-service" : command.reviewerId());
                trace(resultId);
            }
            log.info("server2 dispatch ok fileId={} sourcePath={} taskId={} resultId={}",
                    command.fileId(), ingress.sourcePath(), taskId, resultId);
            return new Server2DispatchResult(
                    ingress.sourcePath(), taskId, status.isBlank() ? "COMPLETED" : status,
                    resultId, mapping.dataType(), mapping.classification(), watermark);
        } catch (ApiException ex) {
            throw ex;
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new ApiException(ErrorCode.SERVICE_UNAVAILABLE, "分发失败：等待服务器2处理被中断");
        } catch (Exception ex) {
            log.error("server2 dispatch failed fileId={}", command.fileId(), ex);
            throw new ApiException(ErrorCode.BAD_REQUEST, "分发失败：无法将文件提交到服务器2");
        }
    }

    @Override
    public Server2TraceSnapshot queryTrace(String taskId, String resultId) {
        if (!enabled() || token().isBlank()) {
            return Server2TraceSnapshot.unavailable("未配置服务器2");
        }
        try {
            JsonNode task = objectMapper.createObjectNode();
            if (taskId != null && !taskId.isBlank()) {
                String id = taskId.trim();
                task = getOptional("/api/v1/tasks/" + id, "/internal/tasks/" + id);
            }
            String rid = firstNonBlank(resultId, text(task, "result_id"));
            JsonNode provenance = objectMapper.createObjectNode();
            JsonNode verification = objectMapper.createObjectNode();
            if (!rid.isBlank()) {
                String encoded = URLEncoder.encode(rid, StandardCharsets.UTF_8);
                provenance = postOptional("/api/v1/provenance/query?result_id=" + encoded);
                verification = getOptional(
                        "/api/v1/results/" + rid + "/verification",
                        "/internal/results/" + rid + "/verification",
                        "/api/v1/results/" + rid
                );
            }
            return mapTrace(taskId, rid, task, provenance, verification);
        } catch (Exception ex) {
            log.warn("server2 trace query failed taskId={} resultId={}", taskId, resultId, ex);
            return Server2TraceSnapshot.unavailable("服务器2溯源暂不可用");
        }
    }

    private void health() throws IOException, InterruptedException {
        HttpResponse<String> response = send(HttpRequest.newBuilder(uri("/health"))
                .timeout(Duration.ofSeconds(10))
                .GET()
                .build());
        if (response.statusCode() >= 300) {
            throw new ApiException(ErrorCode.SERVICE_UNAVAILABLE, "分发失败：服务器2健康检查未通过");
        }
    }

    private Ingress upload(Server2DispatchCommand command, Server2KindMapper.Mapping mapping, String sha256)
            throws IOException, InterruptedException {
        Ingress chunked = uploadChunked(command, mapping, sha256);
        if (chunked != null) {
            return chunked;
        }
        return uploadMultipart(command, mapping, sha256);
    }

    private Ingress uploadChunked(Server2DispatchCommand command, Server2KindMapper.Mapping mapping, String sha256)
            throws IOException, InterruptedException {
        int requestedChunk = Math.min(MAX_CHUNK_SIZE_BYTES, Math.max(1024, properties.getChunkSizeBytes()));
        ObjectNode initBody = objectMapper.createObjectNode();
        initBody.put("project_id", command.projectId());
        initBody.put("user_id", serviceUser(command));
        initBody.put("file_id", command.fileId());
        initBody.put("file_name", command.fileName());
        initBody.put("filename", command.fileName());
        initBody.put("size_bytes", Files.size(command.localFile()));
        initBody.put("sha256", sha256);
        initBody.put("data_type", mapping.dataType());
        initBody.put("classification", mapping.classification());
        initBody.put("chunk_size", requestedChunk);

        HttpResponse<String> init = send(jsonRequest("POST", "/api/v1/ingest/sessions", initBody));
        boolean v1 = init.statusCode() != 404;
        if (!v1) {
            init = send(jsonRequest("POST", "/internal/uploads", initBody));
        }
        if (init.statusCode() == 404) {
            return null;
        }
        requireOk(init, "分块上传初始化");
        JsonNode initJson = read(init.body());
        String uploadId = first(initJson, "upload_id", "id");
        if (uploadId.isBlank()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "分发失败：服务器2未返回上传会话");
        }
        int chunkSize = initJson.path("chunk_size").asInt(requestedChunk);
        if (chunkSize <= 0) {
            chunkSize = requestedChunk;
        }
        chunkSize = Math.min(MAX_CHUNK_SIZE_BYTES, chunkSize);
        String chunkPathPrefix = v1
                ? "/api/v1/ingest/sessions/" + uploadId + "/chunks/"
                : "/internal/uploads/" + uploadId + "/chunks/";
        putChunks(command.localFile(), chunkPathPrefix, chunkSize, command.fileId());
        ObjectNode completeBody = objectMapper.createObjectNode();
        completeBody.put("sha256", sha256);
        String completePath = v1
                ? "/api/v1/ingest/sessions/" + uploadId + "/complete"
                : "/internal/uploads/" + uploadId + "/complete";
        HttpResponse<String> complete = send(jsonRequest("POST", completePath, completeBody));
        requireOk(complete, "分块上传完成");
        JsonNode completeJson = read(complete.body());
        String sourcePath = first(completeJson, "source_path", "path");
        if (sourcePath.isBlank()) {
            sourcePath = first(initJson, "source_path", "path");
        }
        if (sourcePath.isBlank()) {
            sourcePath = uploadId;
        }
        return new Ingress(sourcePath, uploadId, v1);
    }

    private void putChunks(Path localFile, String chunkPathPrefix, int chunkSize, String fileId)
            throws IOException, InterruptedException {
        long fileSize = Files.size(localFile);
        if (fileSize <= 0) {
            return;
        }
        int total = (int) ((fileSize + chunkSize - 1L) / chunkSize);
        int concurrency = Math.min(chunkConcurrency(), Math.max(1, total));
        long started = System.nanoTime();
        log.info("server2 chunk upload start fileId={} bytes={} chunks={} chunkSize={} concurrency={}",
                fileId, fileSize, total, chunkSize, concurrency);
        try (FileChannel channel = FileChannel.open(localFile, StandardOpenOption.READ)) {
            if (concurrency == 1) {
                for (int index = 0; index < total; index++) {
                    putOneChunk(channel, chunkPathPrefix, index, chunkSize, fileSize);
                }
            } else {
                List<CompletableFuture<Void>> jobs = new ArrayList<>(total);
                for (int index = 0; index < total; index++) {
                    final int chunkNo = index;
                    jobs.add(CompletableFuture.runAsync(() -> {
                        try {
                            putOneChunk(channel, chunkPathPrefix, chunkNo, chunkSize, fileSize);
                        } catch (Exception ex) {
                            throw new CompletionException(ex);
                        }
                    }, chunkExecutor));
                }
                try {
                    CompletableFuture.allOf(jobs.toArray(CompletableFuture[]::new)).join();
                } catch (CompletionException ex) {
                    Throwable cause = ex.getCause() == null ? ex : ex.getCause();
                    if (cause instanceof ApiException api) {
                        throw api;
                    }
                    if (cause instanceof IOException io) {
                        throw io;
                    }
                    if (cause instanceof InterruptedException interrupted) {
                        throw interrupted;
                    }
                    if (cause instanceof RuntimeException runtime) {
                        throw runtime;
                    }
                    throw new IOException(cause);
                }
            }
        }
        log.info("server2 chunk upload done fileId={} chunks={} costMs={}",
                fileId, total, (System.nanoTime() - started) / 1_000_000L);
    }

    private void putOneChunk(FileChannel channel, String chunkPathPrefix, int index, int chunkSize, long fileSize)
            throws IOException, InterruptedException {
        long position = (long) index * (long) chunkSize;
        int length = (int) Math.min(chunkSize, fileSize - position);
        if (length <= 0) {
            return;
        }
        byte[] payload = new byte[length];
        ByteBuffer buffer = ByteBuffer.wrap(payload);
        while (buffer.hasRemaining()) {
            int read = channel.read(buffer, position + buffer.position());
            if (read < 0) {
                throw new IOException("分块读取提前结束 chunk=" + index);
            }
        }
        HttpResponse<String> chunk = send(HttpRequest.newBuilder(uri(chunkPathPrefix + index))
                .timeout(requestTimeout())
                .header("X-Service-Token", token())
                .header("Content-Type", "application/octet-stream")
                .PUT(HttpRequest.BodyPublishers.ofByteArray(payload))
                .build());
        requireOk(chunk, "分块上传");
    }

    private Ingress uploadMultipart(Server2DispatchCommand command, Server2KindMapper.Mapping mapping, String sha256)
            throws IOException, InterruptedException {
        String boundary = "----GdsBoundary" + System.nanoTime();
        byte[] body = buildMultipart(boundary, command, mapping, sha256);
        HttpResponse<String> response = send(HttpRequest.newBuilder(uri("/internal/ingress/files"))
                .timeout(requestTimeout())
                .header("X-Service-Token", token())
                .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                .POST(HttpRequest.BodyPublishers.ofByteArray(body))
                .build());
        if (response.statusCode() == 404) {
            response = send(HttpRequest.newBuilder(uri("/internal/import"))
                    .timeout(requestTimeout())
                    .header("X-Service-Token", token())
                    .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                    .POST(HttpRequest.BodyPublishers.ofByteArray(body))
                    .build());
        }
        requireOk(response, "文件上传");
        JsonNode json = read(response.body());
        String sourcePath = first(json, "source_path", "path");
        String uploadId = first(json, "upload_id", "id");
        if (sourcePath.isBlank() && uploadId.isBlank()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "分发失败：服务器2未返回落盘路径");
        }
        return new Ingress(sourcePath, uploadId, !uploadId.isBlank());
    }

    private JsonNode submitTask(Server2DispatchCommand command, Server2KindMapper.Mapping mapping,
                                String watermark, Ingress ingress) throws IOException, InterruptedException {
        if (ingress.v1() && ingress.uploadId() != null && !ingress.uploadId().isBlank()) {
            ObjectNode v1 = objectMapper.createObjectNode();
            v1.put("project_id", command.projectId());
            v1.put("user_id", serviceUser(command));
            v1.put("upload_id", ingress.uploadId());
            v1.put("data_type", mapping.dataType());
            v1.put("classification", mapping.classification());
            v1.put("watermark_text", watermark);
            HttpResponse<String> v1Response = send(jsonRequest("POST", "/api/v1/tasks", v1));
            if (v1Response.statusCode() != 404) {
                requireAccepted(v1Response, "提交处理任务");
                return read(v1Response.body());
            }
        }
        ObjectNode body = objectMapper.createObjectNode();
        body.put("project_id", command.projectId());
        body.put("user_id", serviceUser(command));
        body.put("data_type", mapping.dataType());
        body.put("source_path", ingress.sourcePath());
        body.put("watermark_text", watermark);
        body.put("classification", mapping.classification());
        body.put("file_id", command.fileId());
        HttpResponse<String> response = send(jsonRequest("POST", "/internal/tasks", body));
        requireAccepted(response, "提交处理任务");
        return read(response.body());
    }

    private JsonNode awaitTask(String taskId, JsonNode submitted) throws IOException, InterruptedException {
        String status = text(submitted, "status").toUpperCase(Locale.ROOT);
        if (isTerminal(status) || taskId.isBlank()) {
            return submitted;
        }
        long deadline = System.currentTimeMillis() + properties.getPollTimeoutMs();
        JsonNode latest = submitted;
        while (System.currentTimeMillis() < deadline) {
            Thread.sleep(Math.max(200, properties.getPollIntervalMs()));
            HttpResponse<String> response = send(HttpRequest.newBuilder(uri("/api/v1/tasks/" + taskId))
                    .timeout(Duration.ofSeconds(30))
                    .header("X-Service-Token", token())
                    .GET()
                    .build());
            if (response.statusCode() == 404) {
                response = send(HttpRequest.newBuilder(uri("/internal/tasks/" + taskId))
                        .timeout(Duration.ofSeconds(30))
                        .header("X-Service-Token", token())
                        .GET()
                        .build());
            }
            requireOk(response, "查询任务状态");
            latest = read(response.body());
            if (isTerminal(text(latest, "status"))) {
                return latest;
            }
        }
        throw new ApiException(ErrorCode.SERVICE_UNAVAILABLE, "分发失败：等待服务器2处理超时");
    }

    private void approve(String resultId, String reviewerId) throws IOException, InterruptedException {
        ObjectNode body = objectMapper.createObjectNode();
        body.put("reviewer_id", reviewerId);
        HttpResponse<String> response = send(jsonRequest("POST", "/api/v1/results/" + resultId + "/approve", body));
        if (response.statusCode() == 404) {
            response = send(jsonRequest("POST", "/internal/results/" + resultId + "/approve", body));
        }
        if (response.statusCode() == 404) {
            log.warn("server2 result {} has no approve endpoint", resultId);
            return;
        }
        requireOk(response, "结果审批");
    }

    private void trace(String resultId) {
        try {
            HttpResponse<String> response = send(HttpRequest.newBuilder(
                            uri("/api/v1/provenance/query?result_id=" + resultId))
                    .timeout(Duration.ofSeconds(15))
                    .header("X-Service-Token", token())
                    .POST(HttpRequest.BodyPublishers.noBody())
                    .build());
            if (response.statusCode() == 404) {
                response = send(HttpRequest.newBuilder(uri("/internal/results/" + resultId + "/verification"))
                        .timeout(Duration.ofSeconds(15))
                        .header("X-Service-Token", token())
                        .GET()
                        .build());
            }
            if (response.statusCode() < 300) {
                log.info("server2 trace resultId={} body={}", resultId, response.body());
            }
        } catch (Exception ex) {
            log.debug("server2 trace skipped resultId={}", resultId, ex);
        }
    }

    private HttpRequest jsonRequest(String method, String path, JsonNode body) throws IOException {
        HttpRequest.Builder builder = HttpRequest.newBuilder(uri(path))
                .timeout(requestTimeout())
                .header("X-Service-Token", token())
                .header("Content-Type", "application/json");
        String json = objectMapper.writeValueAsString(body);
        if ("POST".equals(method)) {
            return builder.POST(HttpRequest.BodyPublishers.ofString(json)).build();
        }
        return builder.PUT(HttpRequest.BodyPublishers.ofString(json)).build();
    }

    private HttpResponse<String> send(HttpRequest request) throws IOException, InterruptedException {
        return httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
    }

    private URI uri(String path) {
        String base = properties.getBaseUrl().replaceAll("/+$", "");
        return URI.create(base + path);
    }

    private String token() {
        return properties.getToken() == null ? "" : properties.getToken().trim();
    }

    private Duration requestTimeout() {
        return Duration.ofMillis(Math.max(30_000, properties.getRequestTimeoutMs()));
    }

    private int chunkConcurrency() {
        return Math.max(1, Math.min(16, properties.getChunkConcurrency()));
    }

    private static String serviceUser(Server2DispatchCommand command) {
        if (command.userId() != null && !command.userId().isBlank()) {
            return command.userId();
        }
        return "server1-service";
    }

    private static String resolveSha256(Server2DispatchCommand command) {
        String fromDb = command.contentHash();
        if (fromDb != null && !fromDb.isBlank()) {
            String trimmed = fromDb.trim();
            int colon = trimmed.indexOf(':');
            return colon >= 0 ? trimmed.substring(colon + 1) : trimmed;
        }
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream in = Files.newInputStream(command.localFile())) {
                byte[] buf = new byte[1024 * 1024];
                int read;
                while ((read = in.read(buf)) > 0) {
                    digest.update(buf, 0, read);
                }
            }
            return HexFormat.of().formatHex(digest.digest());
        } catch (Exception ex) {
            throw new ApiException(ErrorCode.INTERNAL_ERROR, "分发失败：无法计算文件校验值");
        }
    }

    private byte[] buildMultipart(String boundary, Server2DispatchCommand command,
                                  Server2KindMapper.Mapping mapping, String sha256) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        Map<String, String> fields = Map.of(
                "project_id", command.projectId() == null ? "" : command.projectId(),
                "user_id", serviceUser(command),
                "file_id", command.fileId() == null ? "" : command.fileId(),
                "data_type", mapping.dataType(),
                "classification", mapping.classification(),
                "sha256", sha256 == null ? "" : sha256
        );
        for (Map.Entry<String, String> field : fields.entrySet()) {
            writeField(out, boundary, field.getKey(), field.getValue());
        }
        String fileName = command.fileName() == null ? "payload.bin" : command.fileName();
        out.write(("--" + boundary + "\r\n").getBytes(StandardCharsets.UTF_8));
        out.write(("Content-Disposition: form-data; name=\"file\"; filename=\"" + fileName + "\"\r\n").getBytes(StandardCharsets.UTF_8));
        out.write("Content-Type: application/octet-stream\r\n\r\n".getBytes(StandardCharsets.UTF_8));
        Files.copy(command.localFile(), out);
        out.write("\r\n".getBytes(StandardCharsets.UTF_8));
        out.write(("--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8));
        return out.toByteArray();
    }

    private static void writeField(ByteArrayOutputStream out, String boundary, String name, String value) throws IOException {
        out.write(("--" + boundary + "\r\n").getBytes(StandardCharsets.UTF_8));
        out.write(("Content-Disposition: form-data; name=\"" + name + "\"\r\n\r\n").getBytes(StandardCharsets.UTF_8));
        out.write((value == null ? "" : value).getBytes(StandardCharsets.UTF_8));
        out.write("\r\n".getBytes(StandardCharsets.UTF_8));
    }

    private JsonNode read(String body) throws IOException {
        if (body == null || body.isBlank()) {
            return objectMapper.createObjectNode();
        }
        return objectMapper.readTree(body);
    }

    private static String text(JsonNode node, String field) {
        if (node == null || node.path(field).isMissingNode() || node.path(field).isNull()) {
            return "";
        }
        return node.path(field).asText("");
    }

    private static String first(JsonNode node, String... fields) {
        for (String field : fields) {
            String value = text(node, field);
            if (!value.isBlank()) {
                return value;
            }
        }
        return "";
    }

    private static boolean isTerminal(String status) {
        String value = status == null ? "" : status.toUpperCase(Locale.ROOT);
        return value.equals("COMPLETED") || value.equals("FAILED") || value.equals("ERROR")
                || value.equals("SUCCESS") || value.equals("APPROVED");
    }

    private void requireOk(HttpResponse<String> response, String action) {
        int status = response.statusCode();
        if (status >= 200 && status < 300) {
            return;
        }
        log.warn("server2 {} rejected status={} body={}", action, status, response.body());
        if (status == 401 || status == 403) {
            throw new ApiException(ErrorCode.UNAUTHORIZED, "分发失败：服务器2服务令牌无效");
        }
        throw new ApiException(ErrorCode.BAD_REQUEST, "分发失败：" + action + "被服务器2拒绝");
    }

    private void requireAccepted(HttpResponse<String> response, String action) {
        requireOk(response, action);
    }

    private JsonNode getOptional(String... paths) {
        for (String path : paths) {
            try {
                HttpResponse<String> response = send(HttpRequest.newBuilder(uri(path))
                        .timeout(Duration.ofSeconds(15))
                        .header("X-Service-Token", token())
                        .GET()
                        .build());
                if (response.statusCode() >= 200 && response.statusCode() < 300) {
                    return read(response.body());
                }
            } catch (Exception ex) {
                log.debug("server2 GET {} skipped", path, ex);
            }
        }
        return objectMapper.createObjectNode();
    }

    private JsonNode postOptional(String path) {
        try {
            HttpResponse<String> response = send(HttpRequest.newBuilder(uri(path))
                    .timeout(Duration.ofSeconds(15))
                    .header("X-Service-Token", token())
                    .POST(HttpRequest.BodyPublishers.noBody())
                    .build());
            if (response.statusCode() >= 200 && response.statusCode() < 300) {
                return read(response.body());
            }
        } catch (Exception ex) {
            log.debug("server2 POST {} skipped", path, ex);
        }
        return objectMapper.createObjectNode();
    }

    private Server2TraceSnapshot mapTrace(String taskId, String resultId,
                                          JsonNode task, JsonNode provenance, JsonNode verification) {
        JsonNode[] docs = {provenance, verification, task};
        String tid = firstNonBlank(taskId, pick(docs, "task_id"));
        String rid = firstNonBlank(resultId, pick(docs, "result_id"));
        String taskStatus = firstNonBlank(text(task, "status"), pick(docs, "task_status"));
        String resultStatus = pick(docs, "approval_status", "result_status", "status");
        String sourcePath = pick(docs, "source_path", "path");
        String sourceHash = pick(docs, "source_hash", "input_hash", "verification.source_hash");
        String outputHash = pick(docs, "output_hash", "result_hash", "trace_record_hash", "verification.output_hash");
        String watermark = pick(docs, "watermark_text", "watermark");
        Boolean verified = pickBool(docs, "verification.verified", "verified");
        String method = pick(docs, "verification.method", "method");
        Integer filesProcessed = pickInt(docs, "verification.files_processed", "files_processed", "file_count");
        Integer matched = pickInt(docs, "verification.matched", "matched");
        Boolean onChain = pickBool(docs, "besu_anchor.onchain", "besu_anchor.on_chain", "on_chain", "chained");
        String chainTx = pick(docs, "besu_anchor.tx_hash", "besu_anchor.transaction_hash", "tx_hash", "chain_tx");
        String chainBlock = pick(docs, "besu_anchor.block_number", "besu_anchor.block", "block_number", "chain_block");
        String processedAt = pick(docs, "completed_at", "processed_at", "updated_at", "approved_at");
        boolean available = !taskStatus.isBlank() || !resultStatus.isBlank() || verified != null
                || onChain != null || !sourceHash.isBlank() || !outputHash.isBlank()
                || !method.isBlank() || filesProcessed != null;
        String hint = available ? "" : "服务器2未返回溯源数据";
        return new Server2TraceSnapshot(
                available, hint, tid, rid, taskStatus, resultStatus, sourcePath, sourceHash, outputHash,
                watermark, verified, method, filesProcessed, matched, onChain, chainTx, chainBlock, processedAt);
    }

    private static String pick(JsonNode[] docs, String... dotted) {
        for (JsonNode doc : docs) {
            if (doc == null || doc.isMissingNode() || doc.isNull()) {
                continue;
            }
            for (String path : dotted) {
                JsonNode node = doc;
                for (String part : path.split("\\.")) {
                    node = node.path(part);
                }
                if (node.isMissingNode() || node.isNull() || node.isObject() || node.isArray()) {
                    continue;
                }
                String value = node.asText("");
                if (!value.isBlank()) {
                    return value.trim();
                }
            }
        }
        return "";
    }

    private static Boolean pickBool(JsonNode[] docs, String... dotted) {
        String value = pick(docs, dotted);
        if (value.isBlank()) {
            return null;
        }
        if ("true".equalsIgnoreCase(value) || "1".equals(value)) {
            return Boolean.TRUE;
        }
        if ("false".equalsIgnoreCase(value) || "0".equals(value)) {
            return Boolean.FALSE;
        }
        return null;
    }

    private static Integer pickInt(JsonNode[] docs, String... dotted) {
        String value = pick(docs, dotted);
        if (value.isBlank()) {
            return null;
        }
        try {
            return Integer.parseInt(value.replaceAll("[^0-9-]", ""));
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private static String firstNonBlank(String... values) {
        if (values == null) {
            return "";
        }
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    private record Ingress(String sourcePath, String uploadId, boolean v1) {
    }
}
