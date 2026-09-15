package com.geo.data.security.server1.ingest.service;

import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.ingest.controller.dto.DataFileDto;
import com.geo.data.security.server1.ingest.controller.dto.FileVolumeRow;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

public interface FileIngestService {

    PageDto<DataFileDto> listFiles(String projectId, Integer page, Integer pageSize);

    long countAll();

    List<FileVolumeRow> listVolumeRows();

    DataFileDto createFile(String projectId, String kind, String displayName, MultipartFile file);
}
