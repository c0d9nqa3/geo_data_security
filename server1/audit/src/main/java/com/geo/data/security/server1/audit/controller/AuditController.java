package com.geo.data.security.server1.audit.controller;

import com.geo.data.security.server1.audit.service.AuditQueryService;
import com.geo.data.security.server1.audit.controller.dto.AuditEventDto;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/audit")
public class AuditController {

    private final AuditQueryService auditQueryService;

    public AuditController(AuditQueryService auditQueryService) {
        this.auditQueryService = auditQueryService;
    }

    @GetMapping("/events")
    public ApiResponse<List<AuditEventDto>> events(
            @RequestParam(value = "action", required = false) String action,
            @RequestParam(value = "result", required = false) String result) {
        return ApiResponse.ok(RequestContext.requestId(), auditQueryService.listEvents(action, result));
    }
}
