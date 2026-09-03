package com.geo.data.security.server1.ingest.service;

import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.circulation.service.CirculationIntake;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.ingest.controller.dto.DataFileDto;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "stub")
public class StubFileIngestService implements FileIngestService {

    private final List<DataFileDto> files = new CopyOnWriteArrayList<>(List.of(
            new DataFileDto("file_2001", "prj_1001", "城区正射影像库", "tile_A12.tif", "GeoTIFF",
                    1840, "transferred", "sha256:8f3a…c91", "张工", "2026-09-01 15:10")
    ));
    private final AuditRecorder auditRecorder;
    private final CirculationIntake circulationIntake;

    public StubFileIngestService(AuditRecorder auditRecorder, CirculationIntake circulationIntake) {
        this.auditRecorder = auditRecorder;
        this.circulationIntake = circulationIntake;
    }

    @Override
    public List<DataFileDto> listFiles(String projectId) {
        RequestContext.requirePrincipal();
        if (projectId == null || projectId.isBlank()) {
            return new ArrayList<>(files);
        }
        return files.stream().filter(f -> projectId.equals(f.projectId())).toList();
    }

    @Override
    public DataFileDto createFile(String projectId, String kind, String displayName, MultipartFile file) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
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
        auditRecorder.record("upload", projectId, created.id(), null, "上传 " + created.name(), "success");
        circulationIntake.openTicket("file", projectId, created.id(), null, "上传文件审核：" + created.name());
        return created;
    }
}
