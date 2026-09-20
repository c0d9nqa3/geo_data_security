package com.geo.data.security.server1.ingest.controller;

import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiResponse;
import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.ingest.controller.dto.DataFileDto;
import com.geo.data.security.server1.ingest.controller.dto.FileProvenanceDto;
import com.geo.data.security.server1.ingest.service.FileIngestService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/files")
public class FileIngestController {

    private final FileIngestService fileIngestService;

    public FileIngestController(FileIngestService fileIngestService) {
        this.fileIngestService = fileIngestService;
    }

    @GetMapping
    public ApiResponse<PageDto<DataFileDto>> list(
            @RequestParam(value = "projectId", required = false) String projectId,
            @RequestParam(value = "page", required = false) Integer page,
            @RequestParam(value = "pageSize", required = false) Integer pageSize) {
        return ApiResponse.ok(RequestContext.requestId(),
                fileIngestService.listFiles(projectId, page, pageSize));
    }

    @GetMapping("/{id}/provenance")
    public ApiResponse<FileProvenanceDto> provenance(@PathVariable("id") String id) {
        return ApiResponse.ok(RequestContext.requestId(), fileIngestService.getProvenance(id));
    }

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ApiResponse<DataFileDto> upload(
            @RequestParam("projectId") String projectId,
            @RequestParam(value = "kind", required = false) String kind,
            @RequestParam(value = "name", required = false) String name,
            @RequestParam("file") MultipartFile file) {
        return ApiResponse.ok(RequestContext.requestId(),
                fileIngestService.createFile(projectId, kind, name, file));
    }
}
