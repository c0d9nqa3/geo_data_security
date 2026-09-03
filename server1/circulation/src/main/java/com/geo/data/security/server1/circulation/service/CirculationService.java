package com.geo.data.security.server1.circulation.service;

import com.geo.data.security.server1.circulation.controller.dto.CirculationDto;
import com.geo.data.security.server1.circulation.controller.dto.CirculationPageDto;
import com.geo.data.security.server1.circulation.controller.dto.CreateCirculationRequest;
import com.geo.data.security.server1.circulation.controller.dto.ReviewActionRequest;

public interface CirculationService {

    CirculationPageDto listCirculations(String status, Integer page, Integer pageSize);

    CirculationDto getCirculation(String circulationId);

    CirculationDto apply(CreateCirculationRequest request);

    CirculationDto approve(String circulationId, ReviewActionRequest request);

    CirculationDto reject(String circulationId, ReviewActionRequest request);

    CirculationDto distribute(String circulationId);

    void deleteCirculation(String circulationId);
}
