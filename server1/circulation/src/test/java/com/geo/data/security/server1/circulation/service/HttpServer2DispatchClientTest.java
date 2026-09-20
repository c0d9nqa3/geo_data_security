package com.geo.data.security.server1.circulation.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class HttpServer2DispatchClientTest {

    private HttpServer server;
    private Path payload;
    private final Map<String, byte[]> chunks = new ConcurrentHashMap<>();
    private volatile String receivedSha;
    private volatile String receivedType;
    private volatile String receivedClass;
    private volatile String receivedWatermark;
    private volatile String receivedProject;

    @BeforeEach
    void setUp() throws Exception {
        payload = Files.createTempFile("gds-dispatch", ".tif");
        Files.writeString(payload, "fake-dom-bytes-for-server2");
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/health", ex -> json(ex, 200, "{\"status\":\"ok\",\"role\":\"processing_storage_readonly_output\"}"));
        server.createContext("/api/v1", this::notFound);
        server.createContext("/internal/uploads", this::handleUploads);
        server.createContext("/internal/tasks", this::handleTasks);
        server.createContext("/internal/results", this::handleResults);
        server.createContext("/api/v1/provenance", this::handleProvenance);
        server.createContext("/api/v1/results", this::handleV1Results);
        server.setExecutor(Executors.newCachedThreadPool());
        server.start();
    }

    @AfterEach
    void tearDown() throws IOException {
        server.stop(0);
        Files.deleteIfExists(payload);
    }

    @Test
    void dispatchUploadsFileAndSubmitsTaskMetadata() throws Exception {
        Server2DispatchProperties properties = new Server2DispatchProperties();
        properties.setEnabled(true);
        properties.setBaseUrl("http://127.0.0.1:" + server.getAddress().getPort());
        properties.setToken("test-token");
        properties.setChunkSizeBytes(8);
        properties.setChunkConcurrency(4);
        properties.setPollIntervalMs(50);
        properties.setPollTimeoutMs(2000);
        HttpServer2DispatchClient client = new HttpServer2DispatchClient(properties, new ObjectMapper());

        Server2DispatchResult result = client.dispatch(new Server2DispatchCommand(
                "prj_dom_001", "file_dom_1", "sample.tif", "DOM",
                null, payload, "u_zhangsan", "u_admin"));

        assertEquals("COMPLETED", result.status());
        assertEquals("DOM", result.dataType());
        assertEquals("ORTHOIMAGE", result.classification());
        assertEquals("prj_dom_001", receivedProject);
        assertEquals("DOM", receivedType);
        assertEquals("ORTHOIMAGE", receivedClass);
        assertTrue(result.watermark().startsWith("0x"));
        assertEquals(result.watermark(), receivedWatermark);
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        digest.update(Files.readAllBytes(payload));
        assertEquals(HexFormat.of().formatHex(digest.digest()), receivedSha);
        assertEquals("V:/geo_data_security/incoming/file_dom_1/sample.tif", result.sourcePath());
        assertEquals("task-1", result.taskId());
        assertEquals("res-1", result.resultId());
    }

    @Test
    void queryTraceReadsVerificationAndChainAnchor() {
        Server2DispatchProperties properties = new Server2DispatchProperties();
        properties.setEnabled(true);
        properties.setBaseUrl("http://127.0.0.1:" + server.getAddress().getPort());
        properties.setToken("test-token");
        HttpServer2DispatchClient client = new HttpServer2DispatchClient(properties, new ObjectMapper());

        Server2TraceSnapshot snap = client.queryTrace("task-1", "res-1");
        assertTrue(snap.available());
        assertEquals(true, snap.verified());
        assertEquals(true, snap.onChain());
        assertEquals("sandbox_osgb_pixel_extract", snap.method());
        assertEquals(89, snap.filesProcessed());
        assertEquals("0xabc", snap.chainTx());
        assertEquals("141189", snap.chainBlock());
    }

    private void notFound(HttpExchange exchange) throws IOException {
        json(exchange, 404, "{\"detail\":\"not found\"}");
    }

    private void handleUploads(HttpExchange exchange) throws IOException {
        String path = exchange.getRequestURI().getPath();
        String method = exchange.getRequestMethod();
        if ("POST".equals(method) && "/internal/uploads".equals(path)) {
            json(exchange, 200, "{\"upload_id\":\"up-1\",\"chunk_size\":8}");
            return;
        }
        if ("PUT".equals(method) && path.contains("/chunks/")) {
            String idx = path.substring(path.lastIndexOf('/') + 1);
            chunks.put(idx, exchange.getRequestBody().readAllBytes());
            json(exchange, 200, "{\"ok\":true}");
            return;
        }
        if ("POST".equals(method) && path.endsWith("/complete")) {
            ByteArrayOutputStream assembled = new ByteArrayOutputStream();
            for (int i = 0; i < chunks.size(); i++) {
                assembled.write(chunks.get(String.valueOf(i)));
            }
            receivedSha = sha(assembled.toByteArray());
            json(exchange, 200, "{\"source_path\":\"V:/geo_data_security/incoming/file_dom_1/sample.tif\",\"sha256\":\""
                    + receivedSha + "\"}");
            return;
        }
        json(exchange, 404, "{\"detail\":\"not found\"}");
    }

    private void handleTasks(HttpExchange exchange) throws IOException {
        String path = exchange.getRequestURI().getPath();
        if ("POST".equals(exchange.getRequestMethod()) && "/internal/tasks".equals(path)) {
            String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            receivedProject = extract(body, "project_id");
            receivedType = extract(body, "data_type");
            receivedClass = extract(body, "classification");
            receivedWatermark = extract(body, "watermark_text");
            json(exchange, 202, "{\"task_id\":\"task-1\",\"status\":\"COMPLETED\",\"result_id\":\"res-1\"}");
            return;
        }
        if ("GET".equals(exchange.getRequestMethod()) && path.startsWith("/internal/tasks/")) {
            json(exchange, 200, "{\"task_id\":\"task-1\",\"status\":\"COMPLETED\",\"result_id\":\"res-1\"}");
            return;
        }
        json(exchange, 404, "{\"detail\":\"not found\"}");
    }

    private void handleResults(HttpExchange exchange) throws IOException {
        String path = exchange.getRequestURI().getPath();
        if (path.endsWith("/approve")) {
            json(exchange, 200, "{\"result_id\":\"res-1\",\"approval_status\":\"APPROVED\"}");
            return;
        }
        if (path.endsWith("/trace")) {
            json(exchange, 200, "{\"result_id\":\"res-1\",\"trace\":\"ok\"}");
            return;
        }
        json(exchange, 404, "{\"detail\":\"not found\"}");
    }

    private void handleProvenance(HttpExchange exchange) throws IOException {
        exchange.getRequestBody().readAllBytes();
        json(exchange, 200, """
                {"result_id":"res-1","status":"APPROVED","verification":{"verified":true,"method":"sandbox_osgb_pixel_extract","files_processed":89,"matched":89},"besu_anchor":{"onchain":true,"tx_hash":"0xabc","block_number":141189}}
                """);
    }

    private void handleV1Results(HttpExchange exchange) throws IOException {
        if (exchange.getRequestURI().getPath().endsWith("/verification")) {
            json(exchange, 200, "{\"verified\":true,\"method\":\"sandbox_osgb_pixel_extract\",\"files_processed\":89,\"matched\":89}");
            return;
        }
        json(exchange, 200, "{\"result_id\":\"res-1\",\"status\":\"APPROVED\"}");
    }

    private static void json(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }

    private static String sha(byte[] data) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    private static String extract(String json, String field) {
        String key = "\"" + field + "\"";
        int idx = json.indexOf(key);
        if (idx < 0) {
            return "";
        }
        int colon = json.indexOf(':', idx);
        int start = json.indexOf('"', colon + 1) + 1;
        int end = json.indexOf('"', start);
        return json.substring(start, end);
    }
}
