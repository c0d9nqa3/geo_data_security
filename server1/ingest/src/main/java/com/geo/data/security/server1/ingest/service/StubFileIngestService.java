package com.geo.data.security.server1.ingest.service;

import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.circulation.service.CirculationIntake;
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
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.time.YearMonth;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "stub")
public class StubFileIngestService implements FileIngestService {

    private final List<DataFileDto> files = new CopyOnWriteArrayList<>(List.of(
            new DataFileDto("file_2001", "prj_1001", "城区正射影像库", "tile_A12.tif", "DOM",
                    1840, "transferred", "sha256:8f3a…c91", "张工", "2026-09-01 15:10")
    ));
    private final Map<String, String> uploaders = new ConcurrentHashMap<>(Map.of("file_2001", "u_admin"));
    private final List<FileVolumeRow> volumeRows = demoVolumeRows();
    private final AuditRecorder auditRecorder;
    private final CirculationIntake circulationIntake;

    public StubFileIngestService(AuditRecorder auditRecorder, CirculationIntake circulationIntake) {
        this.auditRecorder = auditRecorder;
        this.circulationIntake = circulationIntake;
    }

    @Override
    public PageDto<DataFileDto> listFiles(String projectId, Integer page, Integer pageSize) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        List<DataFileDto> filtered = files.stream()
                .filter(f -> DataScope.canSeeAll(principal) || DataScope.isOwner(principal, uploaders.get(f.id())))
                .filter(f -> projectId == null || projectId.isBlank() || projectId.equals(f.projectId()))
                .toList();
        return PageDto.slice(filtered, page, pageSize);
    }

    @Override
    public long countAll() {
        RequestContext.requirePrincipal();
        return files.size();
    }

    @Override
    public List<FileVolumeRow> listVolumeRows() {
        RequestContext.requirePrincipal();
        return List.copyOf(volumeRows);
    }

    @Override
    public DataFileDto createFile(String projectId, String kind, String displayName, MultipartFile file) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        Checks.requirePermission(principal, "upload");
        if (file == null || file.isEmpty()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "请选择要上传的本地文件");
        }
        String original = file.getOriginalFilename() == null || file.getOriginalFilename().isBlank()
                ? "unnamed.bin"
                : file.getOriginalFilename();
        String fileName = displayName == null || displayName.isBlank() ? original : displayName.trim();
        String kindUi = (kind == null || kind.isBlank()) ? JdbcFileIngestService.inferKind(fileName) : kind.trim();
        String stamp = TimeFormats.DISPLAY.format(LocalDateTime.now());
        double sizeMb = Math.round(file.getSize() / 1024.0 / 1024.0 * 100.0) / 100.0;
        DataFileDto created = new DataFileDto(
                "file_" + System.currentTimeMillis(),
                projectId,
                projectId,
                fileName,
                kindUi,
                sizeMb,
                "uploaded",
                "sha256:demo",
                principal.displayName(),
                stamp
        );
        files.add(0, created);
        uploaders.put(created.id(), principal.userId());
        auditRecorder.record("upload", projectId, created.id(), null, "上传 " + created.name(), "success");
        circulationIntake.openTicket("file", projectId, created.id(), null, "上传文件审核：" + created.name());
        return created;
    }

    @Override
    public FileProvenanceDto getProvenance(String fileIdRaw) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        String fileId = Checks.requireText(fileIdRaw, "文件不存在");
        DataFileDto file = files.stream().filter(item -> fileId.equals(item.id())).findFirst()
                .orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND, "文件不存在"));
        DataScope.requireVisible(principal, uploaders.get(file.id()));
        boolean demo = "file_2001".equals(file.id()) || "transferred".equals(file.status());
        FileProvenanceAssembler.Circ circ = new FileProvenanceAssembler.Circ(
                demo ? "approved" : "pending",
                demo ? "dispatched" : "none",
                file.uploadedBy(),
                demo ? "管理员" : "",
                demo ? "演示分发" : "上传文件审核：" + file.name(),
                file.uploadedAt(),
                file.uploadedAt(),
                demo ? "res_demo" : ""
        );
        Server2TraceSnapshot live = demo
                ? new Server2TraceSnapshot(
                true, "", "task_demo", "res_demo", "COMPLETED", "APPROVED",
                "/demo/" + file.name(), file.hash(), "sha256:result", "0xdemo",
                true, "sandbox_osgb_pixel_extract", 89, 89, true,
                "0xb2b3c3de", "141189", file.uploadedAt())
                : Server2TraceSnapshot.unavailable("演示环境未连接服务器2");
        auditRecorder.record("query_trace", file.projectId(), file.id(), demo ? "task_demo" : null,
                "查看文件溯源 " + file.name(), "success");
        return FileProvenanceAssembler.assemble(
                file.id(), file.name(), file.projectId(), file.projectName(), file.status(),
                file.uploadedBy(), file.uploadedAt(), file.hash(), circ, live,
                demo ? "task_demo" : "", demo ? "res_demo" : "", demo ? "/demo/" + file.name() : "");
    }

    private static List<FileVolumeRow> demoVolumeRows() {
        List<FileVolumeRow> rows = new ArrayList<>();
        YearMonth cursor = YearMonth.now(ZoneId.of("Asia/Shanghai"));
        for (int i = 17; i >= 0; i--) {
            YearMonth ym = cursor.minusMonths(i);
            for (GeoDataKinds.Def def : GeoDataKinds.ALL) {
                long count = switch (def.dbCode()) {
                    case "DLG" -> 620;
                    case "DOM" -> 48;
                    case "DEM" -> 36;
                    case "DRG" -> 40;
                    case "GEO_ENTITY" -> 95;
                    case "MESH" -> 28;
                    case "POINT_CLOUD" -> 54;
                    default -> 10;
                };
                count += ym.getMonthValue() * 2L;
                long bytes = switch (def.dbCode()) {
                    case "DLG" -> 25L * 1024 * 1024;
                    case "DOM" -> 420L * 1024 * 1024;
                    case "DEM" -> 90L * 1024 * 1024;
                    case "DRG" -> 180L * 1024 * 1024;
                    case "GEO_ENTITY" -> 40L * 1024 * 1024;
                    case "MESH" -> 780L * 1024 * 1024;
                    case "POINT_CLOUD" -> 260L * 1024 * 1024;
                    default -> 8L * 1024 * 1024;
                };
                rows.add(new FileVolumeRow(def.dbCode(), ym.getYear(), ym.getMonthValue(), count, bytes));
            }
        }
        return List.copyOf(rows);
    }
}
