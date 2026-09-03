package com.geo.data.security.server1.ingest.service;

import com.geo.data.security.server1.ingest.controller.dto.DataFileDto;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

public interface FileIngestService {

    List<DataFileDto> listFiles(String projectId);

    DataFileDto createFile(String projectId, String kind, String displayName, MultipartFile file);
}
