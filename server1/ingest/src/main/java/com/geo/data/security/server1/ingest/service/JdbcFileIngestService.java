package com.geo.data.security.server1.ingest.service;

import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.circulation.service.CirculationIntake;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.common.support.Checks;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.ingest.controller.dto.DataFileDto;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "jdbc", matchIfMissing = true)
public class JdbcFileIngestService implements FileIngestService {

    private static final Logger log = LoggerFactory.getLogger(JdbcFileIngestService.class);

    private final JdbcTemplate jdbc;
    private final AuditRecorder auditRecorder;
    private final CirculationIntake circulationIntake;
    private final Path receiveDir;

    public JdbcFileIngestService(JdbcTemplate jdbcTemplate, AuditRecorder auditRecorder,
                                 CirculationIntake circulationIntake,
                                 @Value("${ingest.receive-dir:./data/receive}") String receiveDir) {
        this.jdbc = jdbcTemplate;
        this.auditRecorder = auditRecorder;
        this.circulationIntake = circulationIntake;
        this.receiveDir = Paths.get(receiveDir);
    }

    @Override
    public List<DataFileDto> listFiles(String projectId) {
        RequestContext.requirePrincipal();
        boolean filter = projectId != null && !projectId.isBlank();
        String sql = """
                SELECT f.file_id, f.project_id, p.project_name, f.file_name, f.data_kind,
                       f.size_bytes, f.status, f.content_hash, f.created_at,
                       COALESCE(u.display_name, f.uploaded_by) AS uploader_name
                FROM biz_file f
                LEFT JOIN biz_project p ON p.project_id = f.project_id
                LEFT JOIN sys_user u ON u.user_id = f.uploaded_by
                """ + (filter ? " WHERE f.project_id = ? " : " ") + """
                ORDER BY f.created_at DESC, f.id DESC
                """;
        return filter
                ? jdbc.query(sql, this::mapFile, projectId)
                : jdbc.query(sql, this::mapFile);
    }

    @Override
    @Transactional
    public DataFileDto createFile(String projectIdRaw, String kind, String displayName, MultipartFile file) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        String projectId = Checks.requireText(projectIdRaw, "请选择目标项目");
        if (file == null || file.isEmpty()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "请选择要上传的本地文件");
        }
        String original = safeFileName(file.getOriginalFilename());
        String fileName = clipName(displayName == null || displayName.isBlank() ? original : displayName.trim());
        String kindUi = (kind == null || kind.isBlank()) ? inferKind(original) : kind.trim();
        String kindDb = toDbKind(kindUi);

        List<String> names = jdbc.query(
                "SELECT project_name FROM biz_project WHERE project_id = ? LIMIT 1",
                (rs, i) -> rs.getString("project_name"),
                projectId
        );
        if (names.isEmpty()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "目标项目不存在");
        }
        String projectName = names.get(0);

        String fileId = "file_" + System.currentTimeMillis();
        Path dest = receiveDir.toAbsolutePath().normalize().resolve(fileId).resolve(original);
        String hash;
        try {
            Files.createDirectories(dest.getParent());
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream in = new DigestInputStream(file.getInputStream(), digest);
                 OutputStream out = Files.newOutputStream(dest)) {
                in.transferTo(out);
            }
            hash = "sha256:" + HexFormat.of().formatHex(digest.digest());
        } catch (Exception ex) {
            log.error("receive file failed name={}", original, ex);
            throw new ApiException(ErrorCode.INTERNAL_ERROR, "文件接收失败");
        }

        long sizeBytes = sizeOf(dest);
        String receiveRef = dest.toString();
        LocalDateTime now = LocalDateTime.now();
        try {
            jdbc.update(
                    """
                    INSERT INTO biz_file
                      (file_id, project_id, file_name, data_kind, size_bytes, content_hash, status,
                       uploaded_by, temp_receive_ref, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'uploaded', ?, ?, ?)
                    """,
                    fileId, projectId, fileName, kindDb, sizeBytes, hash, principal.userId(),
                    receiveRef, Timestamp.valueOf(now)
            );
        } catch (RuntimeException ex) {
            try {
                Files.deleteIfExists(dest);
            } catch (IOException ignored) {
                // keep original insert failure
            }
            throw ex;
        }
        auditRecorder.record("upload", projectId, fileId, null, "上传 " + fileName, "success");
        circulationIntake.openTicket("file", projectId, fileId, null, "上传文件审核：" + fileName);
        return new DataFileDto(
                fileId, projectId, projectName, fileName, toUiKind(kindDb),
                bytesToMb(sizeBytes), "uploaded", hash,
                principal.displayName(), TimeFormats.DISPLAY.format(now)
        );
    }

    private DataFileDto mapFile(java.sql.ResultSet rs, int i) throws java.sql.SQLException {
        long sizeBytes = rs.getLong("size_bytes");
        return new DataFileDto(
                rs.getString("file_id"),
                rs.getString("project_id"),
                TimeFormats.nullToEmpty(rs.getString("project_name")),
                rs.getString("file_name"),
                toUiKind(rs.getString("data_kind")),
                bytesToMb(sizeBytes),
                rs.getString("status"),
                TimeFormats.nullToEmpty(rs.getString("content_hash")),
                rs.getString("uploader_name"),
                TimeFormats.format(rs.getTimestamp("created_at"))
        );
    }

    static String toDbKind(String uiKind) {
        return switch (uiKind) {
            case "GeoTIFF" -> "GeoTIFF";
            case "SHP/GeoJSON" -> "SHP_GEOJSON";
            case "DLG" -> "DLG";
            case "OSGB" -> "OSGB";
            default -> "OTHER";
        };
    }

    static String toUiKind(String dbKind) {
        if (dbKind == null) {
            return "其他";
        }
        return switch (dbKind.toUpperCase(Locale.ROOT)) {
            case "GEOTIFF" -> "GeoTIFF";
            case "SHP_GEOJSON" -> "SHP/GeoJSON";
            case "DLG" -> "DLG";
            case "OSGB" -> "OSGB";
            default -> "其他";
        };
    }

    static String inferKind(String fileName) {
        String lower = fileName.toLowerCase(Locale.ROOT);
        int dot = lower.lastIndexOf('.');
        String ext = dot >= 0 ? lower.substring(dot + 1) : "";
        return switch (ext) {
            case "tif", "tiff" -> "GeoTIFF";
            case "shp", "geojson", "json" -> "SHP/GeoJSON";
            case "dlg" -> "DLG";
            case "osgb" -> "OSGB";
            default -> "其他";
        };
    }

    static String safeFileName(String raw) {
        if (raw == null || raw.isBlank()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "文件名无效");
        }
        String name = Paths.get(raw.replace('\\', '/')).getFileName().toString().trim();
        name = name.replaceAll("[\\\\/:*?\"<>|]", "_");
        if (name.isBlank() || name.contains("..")) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "文件名无效");
        }
        return clipName(name);
    }

    static String clipName(String name) {
        return name.length() <= 255 ? name : name.substring(0, 255);
    }

    static double bytesToMb(long sizeBytes) {
        return Math.round(sizeBytes / 1024.0 / 1024.0 * 100.0) / 100.0;
    }

    static long sizeOf(Path dest) {
        try {
            return Files.size(dest);
        } catch (IOException e) {
            return 0L;
        }
    }
}
