package com.geo.data.security.server1.circulation.service;

import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.circulation.controller.dto.CirculationDto;
import com.geo.data.security.server1.circulation.controller.dto.CirculationPageDto;
import com.geo.data.security.server1.circulation.controller.dto.CreateCirculationRequest;
import com.geo.data.security.server1.circulation.controller.dto.ReviewActionRequest;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.common.support.Checks;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "stub")
public class StubCirculationService implements CirculationService, CirculationIntake {

    private final List<CirculationDto> items = new CopyOnWriteArrayList<>(List.of(
            new CirculationDto("cir_5001", "task", "prj_1001", "城区正射影像库", "task_3001", "file_2001",
                    "tile_A12.tif", "res_4001", "u_admin", "系统管理员", "", "pending",
                    "提交任务审核", "", "project_members", "2026-09-04 16:10", "none",
                    "", "2026-09-01 16:10")
    ));
    private final Set<String> deletedIds = ConcurrentHashMap.newKeySet();
    private final AuditRecorder auditRecorder;

    public StubCirculationService(AuditRecorder auditRecorder) {
        this.auditRecorder = auditRecorder;
    }

    @Override
    public CirculationPageDto listCirculations(String status, Integer page, Integer pageSize) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        List<CirculationDto> filtered = items.stream()
                .filter(item -> !deletedIds.contains(item.id()))
                .filter(item -> {
                    if (principal.hasPermission("review")) {
                        return true;
                    }
                    return principal.userId().equals(item.applyUserId()) && !"pending".equals(item.status());
                })
                .filter(item -> status == null || status.isBlank() || status.equals(item.status()))
                .toList();
        return CirculationPageDto.slice(filtered, page, pageSize);
    }

    @Override
    public CirculationDto getCirculation(String circulationId) {
        return requireVisible(circulationId);
    }

    @Override
    public void openTicket(String applyType, String projectId, String fileId, String taskId, String purpose) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        String id = "cir_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);
        items.add(0, new CirculationDto(
                id, applyType, projectId, projectId, taskId, fileId, fileId, null,
                principal.userId(), principal.displayName(), "", "pending",
                purpose, "", "project_members", "", "none", "", "now"
        ));
        auditRecorder.record("apply_circulation", projectId, fileId, taskId,
                "提交待办 " + id, "success");
    }

    @Override
    public CirculationDto apply(CreateCirculationRequest request) {
        throw new ApiException(ErrorCode.BAD_REQUEST, "请在项目管理、文件管理或任务管理中提交，流转待办会自动生成");
    }

    @Override
    public CirculationDto approve(String circulationId, ReviewActionRequest request) {
        return review(circulationId, "approved", request);
    }

    @Override
    public CirculationDto reject(String circulationId, ReviewActionRequest request) {
        return review(circulationId, "rejected", request);
    }

    @Override
    public CirculationDto distribute(String circulationId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        Checks.requirePermission(principal, "review");
        CirculationDto current = requireVisible(circulationId);
        if (!"approved".equals(current.status())) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "仅审核通过后可提交分发授权");
        }
        CirculationDto updated = copy(current, current.status(), current.comment(), current.reviewUser(), "dispatched");
        replace(updated);
        auditRecorder.record("distribute", current.projectId(), current.fileId(), current.taskId(),
                "向服务器2提交授权 " + circulationId, "success");
        return updated;
    }

    @Override
    public void deleteCirculation(String circulationId) {
        CirculationDto current = requireVisible(circulationId);
        deletedIds.add(circulationId);
        auditRecorder.record("delete_circulation", current.projectId(), current.fileId(), current.taskId(),
                "逻辑删除流转单 " + circulationId, "success");
    }

    private CirculationDto review(String circulationId, String status, ReviewActionRequest request) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        Checks.requirePermission(principal, "review");
        if (deletedIds.contains(circulationId)) {
            throw new ApiException(ErrorCode.NOT_FOUND, "流转单不存在");
        }
        for (int i = 0; i < items.size(); i++) {
            CirculationDto current = items.get(i);
            if (current.id().equals(circulationId)) {
                String comment = request == null || request.comment() == null ? "" : request.comment();
                CirculationDto updated = copy(current, status, comment, principal.displayName(), current.distributeStatus());
                items.set(i, updated);
                auditRecorder.record("approved".equals(status) ? "approve" : "reject",
                        current.projectId(), current.fileId(), current.taskId(),
                        ("approved".equals(status) ? "通过 " : "驳回 ") + circulationId, "success");
                return updated;
            }
        }
        throw new ApiException(ErrorCode.NOT_FOUND, "流转单不存在");
    }

    private CirculationDto requireVisible(String circulationId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        for (CirculationDto item : items) {
            if (item.id().equals(circulationId)) {
                if (deletedIds.contains(circulationId)) {
                    throw new ApiException(ErrorCode.NOT_FOUND, "流转单不存在");
                }
                if (principal.hasPermission("review")) {
                    return item;
                }
                if (!principal.userId().equals(item.applyUserId()) || "pending".equals(item.status())) {
                    throw new ApiException(ErrorCode.FORBIDDEN, "无权查看该待办");
                }
                return item;
            }
        }
        throw new ApiException(ErrorCode.NOT_FOUND, "流转单不存在");
    }

    private void replace(CirculationDto updated) {
        for (int i = 0; i < items.size(); i++) {
            if (items.get(i).id().equals(updated.id())) {
                items.set(i, updated);
                return;
            }
        }
    }

    private static CirculationDto copy(CirculationDto current, String status, String comment,
                                       String reviewUser, String distributeStatus) {
        return new CirculationDto(
                current.id(), current.applyType(), current.projectId(), current.projectName(), current.taskId(),
                current.fileId(), current.fileName(), current.resultId(), current.applyUserId(),
                current.applyUser(), reviewUser, status, current.purpose(), comment,
                current.authorizeScope(), current.expireAt(), distributeStatus,
                current.resultHash(), current.createdAt()
        );
    }
}
