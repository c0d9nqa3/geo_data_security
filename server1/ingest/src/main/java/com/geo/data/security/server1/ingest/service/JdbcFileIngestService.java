package com.geo.data.security.server1.ingest.service;

import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.circulation.service.CirculationIntake;
import com.geo.data.security.server1.circulation.service.Server2DispatchClient;
import com.geo.data.security.server1.circulation.service.Server2TraceSnapshot;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.common.support.Checks;
import com.geo.data.security.server1.common.support.DataScope;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.ingest.controller.dto.DataFileDto;
import com.geo.data.security.server1.ingest.controller.dto.FileProvenanceDto;
import com.geo.data.security.server1.ingest.controller.dto.FileVolumeRow;
import com.geo.data.security.server1.ingest.support.GeoDataKinds;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "jdbc", matchIfMissing = true)
public class JdbcFileIngestService implements FileIngestService {

    private static final Logger log = LoggerFactory.getLogger(JdbcFileIngestService.class);
    private static final int IO_BUFFER_BYTES = 1024 * 1024;

    private final JdbcTemplate jdbc;
    private final AuditRecorder auditRecorder;
    private final CirculationIntake circulationIntake;
    private final Server2DispatchClient server2DispatchClient;
    private final Path receiveDir;

    public JdbcFileIngestService(JdbcTemplate jdbcTemplate, AuditRecorder auditRecorder,
                                 CirculationIntake circulationIntake,
                                 Server2DispatchClient server2DispatchClient,
                                 @Value("${ingest.receive-dir:./data/receive}") String receiveDir) {
        this.jdbc = jdbcTemplate;
        this.auditRecorder = auditRecorder;
        this.circulationIntake = circulationIntake;
        this.server2DispatchClient = server2DispatchClient;
        this.receiveDir = Paths.get(receiveDir);
    }

    @Override
    public PageDto<DataFileDto> listFiles(String projectId, Integer page, Integer pageSize) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        DataScope.restrictToOwner(where, args, principal, "f.uploaded_by");
        if (projectId != null && !projectId.isBlank()) {
            where.append(" AND f.project_id = ?");
            args.add(projectId.trim());
        }
        Long total = jdbc.queryForObject("SELECT COUNT(*) FROM biz_file f" + where, Long.class, args.toArray());
        long count = total == null ? 0 : total;
        int size = PageDto.normalizeSize(pageSize);
        int pages = PageDto.totalPages(count, size);
        int current = PageDto.normalizePage(page, pages);
        int offset = (current - 1) * size;
        String sql = """
                SELECT f.file_id, f.project_id, p.project_name, f.file_name, f.data_kind,
                       f.size_bytes, f.status, f.content_hash, f.created_at,
                       COALESCE(u.display_name, f.uploaded_by) AS uploader_name
                FROM biz_file f
                LEFT JOIN biz_project p ON p.project_id = f.project_id
                LEFT JOIN sys_user u ON u.user_id = f.uploaded_by
                """ + where + " ORDER BY f.created_at DESC, f.id DESC LIMIT ?, ?";
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(offset);
        pageArgs.add(size);
        List<DataFileDto> items = jdbc.query(sql, this::mapFile, pageArgs.toArray());
        return PageDto.of(items, count, current, size);
    }

    @Override
    public long countAll() {
        RequestContext.requirePrincipal();
        Long total = jdbc.queryForObject("SELECT COUNT(*) FROM biz_file", Long.class);
        return total == null ? 0 : total;
    }

    @Override
    public List<FileVolumeRow> listVolumeRows() {
        RequestContext.requirePrincipal();
        return jdbc.query("""
                SELECT data_kind,
                       YEAR(COALESCE(created_at, updated_at, NOW())) AS y,
                       MONTH(COALESCE(created_at, updated_at, NOW())) AS m,
                       COUNT(*) AS cnt,
                       COALESCE(SUM(size_bytes), 0) AS bytes
                FROM biz_file
                GROUP BY data_kind, YEAR(COALESCE(created_at, updated_at, NOW())),
                         MONTH(COALESCE(created_at, updated_at, NOW()))
                """, (rs, i) -> new FileVolumeRow(
                rs.getString("data_kind"),
                rs.getInt("y"),
                rs.getInt("m"),
                rs.getLong("cnt"),
                rs.getLong("bytes")
        ));
    }

    @Override
    public DataFileDto createFile(String projectIdRaw, String kind, String displayName, MultipartFile file) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        Checks.requirePermission(principal, "upload");
        String projectId = Checks.requireText(projectIdRaw, "请选择目标项目");
        if (file == null || file.isEmpty()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "请选择要上传的本地文件");
        }
        String original = safeFileName(file.getOriginalFilename());
        String fileName = clipName(displayName == null || displayName.isBlank() ? original : displayName.trim());
        String kindUi = (kind == null || kind.isBlank()) ? inferKind(original) : kind.trim();
        String kindDb = toDbKind(kindUi);

        List<ProjectRef> projects = jdbc.query(
                "SELECT project_name, owner_user_id FROM biz_project WHERE project_id = ? LIMIT 1",
                (rs, i) -> new ProjectRef(rs.getString("project_name"), rs.getString("owner_user_id")),
                projectId
        );
        if (projects.isEmpty()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "目标项目不存在");
        }
        ProjectRef project = projects.get(0);
        if (!DataScope.canSeeAll(principal) && !DataScope.isOwner(principal, project.ownerUserId())) {
            throw new ApiException(ErrorCode.FORBIDDEN, "只能向自己新建的项目上传文件");
        }
        String projectName = project.projectName();

        String fileId = "file_" + System.currentTimeMillis();
        Path dest = receiveDir.toAbsolutePath().normalize().resolve(fileId).resolve(original);
        String hash;
        long started = System.nanoTime();
        try {
            Files.createDirectories(dest.getParent());
            hash = storeUploadedFile(file, dest);
        } catch (Exception ex) {
            log.error("receive file failed name={}", original, ex);
            throw new ApiException(ErrorCode.INTERNAL_ERROR, "文件接收失败");
        }
        long sizeBytes = sizeOf(dest);
        log.info("receive file done name={} bytes={} costMs={}", original, sizeBytes,
                (System.nanoTime() - started) / 1_000_000L);
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

    @Override
    public FileProvenanceDto getProvenance(String fileIdRaw) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        String fileId = Checks.requireText(fileIdRaw, "文件不存在");
        List<FileRow> files = jdbc.query(
                """
                SELECT f.file_id, f.project_id, p.project_name, f.file_name, f.status, f.content_hash,
                       f.uploaded_by, f.created_at, f.server2_task_id, f.server2_result_id,
                       f.server2_source_path, f.server2_ref,
                       COALESCE(u.display_name, f.uploaded_by) AS uploader_name
                FROM biz_file f
                LEFT JOIN biz_project p ON p.project_id = f.project_id
                LEFT JOIN sys_user u ON u.user_id = f.uploaded_by
                WHERE f.file_id = ?
                LIMIT 1
                """,
                (rs, i) -> new FileRow(
                        rs.getString("file_id"),
                        rs.getString("project_id"),
                        TimeFormats.nullToEmpty(rs.getString("project_name")),
                        rs.getString("file_name"),
                        TimeFormats.nullToEmpty(rs.getString("status")),
                        TimeFormats.nullToEmpty(rs.getString("content_hash")),
                        rs.getString("uploaded_by"),
                        TimeFormats.nullToEmpty(rs.getString("uploader_name")),
                        TimeFormats.format(rs.getTimestamp("created_at")),
                        TimeFormats.nullToEmpty(rs.getString("server2_task_id")),
                        TimeFormats.nullToEmpty(rs.getString("server2_result_id")),
                        TimeFormats.nullToEmpty(rs.getString("server2_source_path")),
                        TimeFormats.nullToEmpty(rs.getString("server2_ref"))
                ),
                fileId
        );
        if (files.isEmpty()) {
            throw new ApiException(ErrorCode.NOT_FOUND, "文件不存在");
        }
        FileRow file = files.get(0);
        DataScope.requireVisible(principal, file.uploadedBy());

        List<FileProvenanceAssembler.Circ> circs = jdbc.query(
                """
                SELECT c.status, c.distribute_status, c.comment_text, c.result_id, c.created_at, c.updated_at,
                       COALESCE(au.display_name, c.apply_user_id) AS apply_name,
                       ru.display_name AS review_name
                FROM biz_circulation c
                LEFT JOIN sys_user au ON au.user_id = c.apply_user_id
                LEFT JOIN sys_user ru ON ru.user_id = c.review_user_id
                WHERE c.file_id = ? AND COALESCE(c.deleted, 0) = 0
                ORDER BY CASE WHEN c.distribute_status = 'dispatched' THEN 0
                              WHEN c.distribute_status = 'failed' THEN 1
                              ELSE 2 END,
                         COALESCE(c.updated_at, c.created_at) DESC, c.id DESC
                LIMIT 1
                """,
                (rs, i) -> new FileProvenanceAssembler.Circ(
                        TimeFormats.nullToEmpty(rs.getString("status")),
                        TimeFormats.nullToEmpty(rs.getString("distribute_status")),
                        TimeFormats.nullToEmpty(rs.getString("apply_name")),
                        TimeFormats.nullToEmpty(rs.getString("review_name")),
                        TimeFormats.nullToEmpty(rs.getString("comment_text")),
                        TimeFormats.format(rs.getTimestamp("created_at")),
                        TimeFormats.format(rs.getTimestamp("updated_at")),
                        TimeFormats.nullToEmpty(rs.getString("result_id"))
                ),
                fileId
        );
        FileProvenanceAssembler.Circ circ = circs.isEmpty() ? null : circs.get(0);
        FileProvenanceAssembler.Ids parsed = FileProvenanceAssembler.parseComment(circ == null ? "" : circ.comment());
        String taskId = FileProvenanceAssembler.firstNonBlank(file.server2TaskId(), parsed.taskId());
        String resultId = FileProvenanceAssembler.firstNonBlank(
                file.server2ResultId(), file.server2Ref(), circ == null ? "" : circ.resultId(), parsed.resultId());
        String sourcePath = FileProvenanceAssembler.firstNonBlank(file.server2SourcePath(), parsed.sourcePath());

        Server2TraceSnapshot live = Server2TraceSnapshot.unavailable("");
        if (!taskId.isBlank() || !resultId.isBlank()) {
            live = server2DispatchClient.queryTrace(taskId, resultId);
            taskId = FileProvenanceAssembler.firstNonBlank(taskId, live.taskId());
            resultId = FileProvenanceAssembler.firstNonBlank(resultId, live.resultId());
            sourcePath = FileProvenanceAssembler.firstNonBlank(sourcePath, live.sourcePath());
        }

        if ((file.server2TaskId().isBlank() && !taskId.isBlank())
                || (file.server2ResultId().isBlank() && !resultId.isBlank())) {
            jdbc.update(
                    """
                    UPDATE biz_file
                    SET server2_task_id = CASE WHEN ? = '' THEN server2_task_id ELSE ? END,
                        server2_result_id = CASE WHEN ? = '' THEN server2_result_id ELSE ? END,
                        server2_source_path = CASE WHEN ? = '' THEN server2_source_path ELSE ? END,
                        server2_ref = CASE WHEN ? = '' THEN server2_ref ELSE ? END,
                        updated_at = ?
                    WHERE file_id = ?
                    """,
                    taskId, taskId, resultId, resultId, sourcePath, sourcePath, resultId, resultId,
                    Timestamp.valueOf(LocalDateTime.now()), fileId
            );
        }

        FileProvenanceDto dto = FileProvenanceAssembler.assemble(
                file.fileId(), file.fileName(), file.projectId(), file.projectName(), file.status(),
                file.uploaderName(), file.uploadedAt(), file.contentHash(), circ, live,
                taskId, resultId, sourcePath
        );
        auditRecorder.record("query_trace", file.projectId(), file.fileId(), taskId,
                "查看文件溯源 " + file.fileName(), "success");
        return dto;
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
        return GeoDataKinds.toDbCode(uiKind);
    }

    static String toUiKind(String dbKind) {
        return GeoDataKinds.toUiLabel(dbKind);
    }

    static String inferKind(String fileName) {
        return GeoDataKinds.inferUiKind(fileName);
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

    private record ProjectRef(String projectName, String ownerUserId) {
    }

    private record FileRow(
            String fileId,
            String projectId,
            String projectName,
            String fileName,
            String status,
            String contentHash,
            String uploadedBy,
            String uploaderName,
            String uploadedAt,
            String server2TaskId,
            String server2ResultId,
            String server2SourcePath,
            String server2Ref
    ) {
    }

    static long sizeOf(Path dest) {
        try {
            return Files.size(dest);
        } catch (IOException e) {
            return 0L;
        }
    }

    private static String storeUploadedFile(MultipartFile file, Path dest) throws Exception {
        Path part = dest.resolveSibling(dest.getFileName().toString() + ".part");
        Files.deleteIfExists(part);
        Files.deleteIfExists(dest);
        try {
            if (tryTransferTo(file, part)) {
                String hash = hashFile(part);
                moveCompleted(part, dest);
                return hash;
            }
            Files.deleteIfExists(part);
            return copyAndHash(file.getInputStream(), dest);
        } catch (Exception ex) {
            Files.deleteIfExists(part);
            Files.deleteIfExists(dest);
            throw ex;
        }
    }

    private static boolean tryTransferTo(MultipartFile file, Path part) {
        try {
            file.transferTo(part);
            return Files.isRegularFile(part) && (file.getSize() <= 0 || Files.size(part) > 0);
        } catch (Exception ex) {
            return false;
        }
    }

    private static void moveCompleted(Path part, Path dest) throws IOException {
        try {
            Files.move(part, dest, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } catch (AtomicMoveNotSupportedException ex) {
            Files.move(part, dest, StandardCopyOption.REPLACE_EXISTING);
        }
    }

    private static String copyAndHash(InputStream in, Path dest) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream buffered = new DigestInputStream(new BufferedInputStream(in, IO_BUFFER_BYTES), digest);
             OutputStream out = new BufferedOutputStream(Files.newOutputStream(dest), IO_BUFFER_BYTES)) {
            buffered.transferTo(out);
        }
        return "sha256:" + HexFormat.of().formatHex(digest.digest());
    }

    private static String hashFile(Path path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream in = new DigestInputStream(new BufferedInputStream(Files.newInputStream(path), IO_BUFFER_BYTES), digest)) {
            in.transferTo(OutputStream.nullOutputStream());
        }
        return "sha256:" + HexFormat.of().formatHex(digest.digest());
    }
}
