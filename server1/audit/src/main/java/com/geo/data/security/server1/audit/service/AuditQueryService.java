package com.geo.data.security.server1.audit.service;

import com.geo.data.security.server1.audit.controller.dto.AuditEventDto;
import com.geo.data.security.server1.common.web.PageDto;

public interface AuditQueryService {

    PageDto<AuditEventDto> listEvents(String action, String resultStatus, Integer page, Integer pageSize);

    java.util.Map<String, Long> countByDay(java.time.LocalDate fromInclusive);
}
