import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.ByteArrayOutputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;

public class FakeServer2 {
    private static final Path ROOT = Path.of("tests", "fake_server2_inbox");
    private static final Map<String, Map<Integer, byte[]>> CHUNKS = new ConcurrentHashMap<>();
    private static final Map<String, String> META = new ConcurrentHashMap<>();

    public static void main(String[] args) throws Exception {
        Files.createDirectories(ROOT);
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 19081), 0);
        server.createContext("/health", ex -> json(ex, 200,
                "{\"status\":\"ok\",\"role\":\"processing_storage_readonly_output\"}"));
        server.createContext("/internal/uploads", FakeServer2::uploads);
        server.createContext("/internal/tasks", FakeServer2::tasks);
        server.createContext("/internal/results", FakeServer2::results);
        server.setExecutor(Executors.newCachedThreadPool());
        server.start();
        System.out.println("fake server2 listening on http://127.0.0.1:19081");
    }

    private static void uploads(HttpExchange ex) throws java.io.IOException {
        String path = ex.getRequestURI().getPath();
        String method = ex.getRequestMethod();
        byte[] body = ex.getRequestBody().readAllBytes();
        if ("POST".equals(method) && "/internal/uploads".equals(path)) {
            META.put("init", new String(body, StandardCharsets.UTF_8));
            CHUNKS.put("up-live", new ConcurrentHashMap<>());
            json(ex, 200, "{\"upload_id\":\"up-live\",\"chunk_size\":8388608}");
            return;
        }
        if ("PUT".equals(method) && path.contains("/chunks/")) {
            int idx = Integer.parseInt(path.substring(path.lastIndexOf('/') + 1));
            CHUNKS.computeIfAbsent("up-live", k -> new ConcurrentHashMap<>()).put(idx, body);
            json(ex, 200, "{\"ok\":true}");
            return;
        }
        if ("POST".equals(method) && path.endsWith("/complete")) {
            Map<Integer, byte[]> parts = CHUNKS.getOrDefault("up-live", Map.of());
            ByteArrayOutputStream assembled = new ByteArrayOutputStream();
            for (int i = 0; i < parts.size(); i++) {
                assembled.write(parts.getOrDefault(i, new byte[0]));
            }
            String init = META.getOrDefault("init", "{}");
            String fileId = extract(init, "file_id");
            String name = extract(init, "file_name");
            if (fileId.isBlank()) fileId = "unknown";
            if (name.isBlank()) name = "payload.bin";
            Path dir = ROOT.resolve(fileId);
            Files.createDirectories(dir);
            Path dest = dir.resolve(name);
            Files.write(dest, assembled.toByteArray());
            Files.writeString(dir.resolve("meta.json"), init, StandardCharsets.UTF_8);
            String source = dest.toAbsolutePath().toString().replace('\\', '/');
            json(ex, 200, "{\"source_path\":\"" + source + "\",\"bytes\":" + assembled.size() + "}");
            return;
        }
        json(ex, 404, "{\"detail\":\"not found\"}");
    }

    private static void tasks(HttpExchange ex) throws java.io.IOException {
        byte[] body = ex.getRequestBody().readAllBytes();
        if ("POST".equals(ex.getRequestMethod()) && "/internal/tasks".equals(ex.getRequestURI().getPath())) {
            Files.write(ROOT.resolve("last_task.json"), body);
            json(ex, 202, "{\"task_id\":\"task-live\",\"status\":\"COMPLETED\",\"result_id\":\"res-live\"}");
            return;
        }
        if ("GET".equals(ex.getRequestMethod())) {
            json(ex, 200, "{\"task_id\":\"task-live\",\"status\":\"COMPLETED\",\"result_id\":\"res-live\"}");
            return;
        }
        json(ex, 404, "{\"detail\":\"not found\"}");
    }

    private static void results(HttpExchange ex) throws java.io.IOException {
        String path = ex.getRequestURI().getPath();
        if (path.endsWith("/approve")) {
            json(ex, 200, "{\"result_id\":\"res-live\",\"approval_status\":\"APPROVED\"}");
            return;
        }
        if (path.endsWith("/trace")) {
            json(ex, 200, "{\"result_id\":\"res-live\",\"trace\":\"ok\"}");
            return;
        }
        json(ex, 404, "{\"detail\":\"not found\"}");
    }

    private static void json(HttpExchange ex, int status, String body) throws java.io.IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", "application/json");
        ex.sendResponseHeaders(status, bytes.length);
        try (OutputStream os = ex.getResponseBody()) {
            os.write(bytes);
        }
    }

    private static String extract(String json, String field) {
        String key = "\"" + field + "\"";
        int idx = json.indexOf(key);
        if (idx < 0) return "";
        int colon = json.indexOf(':', idx);
        int start = json.indexOf('"', colon + 1) + 1;
        int end = json.indexOf('"', start);
        return json.substring(start, end);
    }
}
