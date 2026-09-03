package com.geo.data.security.server1.audit.service;

import com.geo.data.security.server1.audit.controller.dto.AuditEventDto;

import java.util.List;

public interface AuditQueryService {

    List<AuditEventDto> listEvents(String action, String resultStatus);
}
