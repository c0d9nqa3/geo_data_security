package com.geo.data.security.server1.audit.service;

import com.geo.data.security.server1.audit.controller.dto.AuditEventDto;
import com.geo.data.security.server1.common.context.RequestContext;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "stub")
public class StubAuditQueryService implements AuditQueryService {

    @Override
    public List<AuditEventDto> listEvents(String action, String resultStatus) {
        RequestContext.requirePrincipal();
        List<AuditEventDto> all = List.of(
                new AuditEventDto("aud_1", "2026-09-01 16:06", "张工", "submit_task", "prj_1001",
                        "file_2001", "task_3001", "res_4001",
                        "提交任务 task_3001（GeoTIFF 水印）", "success")
        );
        return all.stream()
                .filter(e -> action == null || action.isBlank() || action.equals(e.action()))
                .filter(e -> resultStatus == null || resultStatus.isBlank() || resultStatus.equals(e.result()))
                .toList();
    }
}
