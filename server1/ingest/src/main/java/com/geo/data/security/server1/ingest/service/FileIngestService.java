package com.geo.data.security.server1.ingest.service;

import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.ingest.controller.dto.DataFileDto;
import org.springframework.web.multipart.MultipartFile;

public interface FileIngestService {

    PageDto<DataFileDto> listFiles(String projectId, Integer page, Integer pageSize);

    long countAll();

    DataFileDto createFile(String projectId, String kind, String displayName, MultipartFile file);
}
