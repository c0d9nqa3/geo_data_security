package com.geo.data.security.server1.audit.service;

import com.geo.data.security.server1.audit.controller.dto.AuditEventDto;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.web.PageDto;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "stub")
public class StubAuditQueryService implements AuditQueryService {

    @Override
    public PageDto<AuditEventDto> listEvents(String action, String resultStatus, Integer page, Integer pageSize) {
        RequestContext.requirePrincipal();
        List<AuditEventDto> all = List.of(
                new AuditEventDto("aud_1", "2026-09-01 16:06", "张工", "submit_task", "prj_1001",
                        "file_2001", "task_3001", "res_4001",
                        "提交任务 task_3001（GeoTIFF 水印）", "success")
        ).stream()
                .filter(e -> action == null || action.isBlank() || action.equals(e.action()))
                .filter(e -> resultStatus == null || resultStatus.isBlank() || resultStatus.equals(e.result()))
                .toList();
        return PageDto.slice(all, page, pageSize);
    }

    @Override
    public Map<String, Long> countByDay(LocalDate fromInclusive) {
        RequestContext.requirePrincipal();
        Map<String, Long> map = new LinkedHashMap<>();
        for (AuditEventDto event : listEvents(null, null, 1, 100).items()) {
            String stamp = event.time();
            if (stamp == null || stamp.length() < 10) {
                continue;
            }
            LocalDate day = LocalDate.parse(stamp.substring(0, 10));
            if (!day.isBefore(fromInclusive)) {
                map.merge(day.toString(), 1L, Long::sum);
            }
        }
        return map;
    }
}
