package com.geo.data.security.server1.task.service;

import com.geo.data.security.server1.audit.service.AuditRecorder;
import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.common.support.Checks;
import com.geo.data.security.server1.common.support.DataScope;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.task.controller.dto.CreateTaskRequest;
import com.geo.data.security.server1.task.controller.dto.TaskDto;
import com.geo.data.security.server1.task.controller.dto.TaskResultDto;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "stub")
public class StubTaskService implements TaskService {

    private final List<Row> rows = new CopyOnWriteArrayList<>();
    private final AuditRecorder auditRecorder;
    private final NoticeRecorder noticeRecorder;

    public StubTaskService(AuditRecorder auditRecorder, NoticeRecorder noticeRecorder) {
        this.auditRecorder = auditRecorder;
        this.noticeRecorder = noticeRecorder;
        rows.add(new Row("task_3001", "task", "prj_1001", "城区正射影像库", "file_2001", "tile_A12.tif",
                "u_admin", "系统管理员", "系统管理员", "approved", "dispatched",
                "处理完成", "提交任务审核", 0, "", "2026-09-01 15:30", "2026-09-01 16:05", false,
                "res_4001", true));
        rows.add(new Row("cir_5001", "task", "prj_1001", "城区正射影像库", "file_2001", "tile_A12.tif",
                "u_admin", "系统管理员", "", "pending", "none",
                "", "提交任务审核", 0, "", "2026-09-01 16:10", "2026-09-01 16:10", false,
                null, false));
        rows.add(new Row("cir_zs_pending", "project", "prj_zs", "张三待审项目", null, "",
                "u_zhangsan", "张三", "", "pending", "none",
                "", "新建项目审核：张三待审项目", 0, "", "2026-09-01 16:20", "2026-09-01 16:20", false,
                null, false));
    }

    @Override
    public PageDto<TaskDto> listTasks(String projectId, String applyType, String status,
                                      Integer page, Integer pageSize) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        List<TaskDto> filtered = rows.stream()
                .map(row -> toDto(row, principal))
                .filter(t -> DataScope.canSeeAll(principal) || DataScope.isOwner(principal, t.applyUserId()))
                .filter(t -> projectId == null || projectId.isBlank() || projectId.equals(t.projectId()))
                .filter(t -> applyType == null || applyType.isBlank() || applyType.equals(t.applyType()))
                .filter(t -> status == null || status.isBlank() || status.equals(t.status()))
                .toList();
        return PageDto.slice(filtered, page, pageSize);
    }

    @Override
    public long countRunning() {
        RequestContext.requirePrincipal();
        return rows.stream()
                .filter(row -> !row.deleted && !"withdrawn".equals(row.circStatus))
                .filter(row -> "pending".equals(row.circStatus)
                        || ("approved".equals(row.circStatus) && !"dispatched".equals(row.dist)))
                .count();
    }

    @Override
    public List<TaskDto> listRecentAll(int limit) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        int size = Math.max(1, Math.min(limit, 50));
        List<TaskDto> all = new ArrayList<>();
        for (Row row : rows) {
            if (!row.deleted && !"withdrawn".equals(row.circStatus)) {
                all.add(toDto(row, principal));
            }
            if (all.size() >= size) {
                break;
            }
        }
        return all;
    }

    @Override
    public Map<String, Long> countCreatedByDay(LocalDate fromInclusive) {
        RequestContext.requirePrincipal();
        Map<String, Long> map = new java.util.LinkedHashMap<>();
        for (Row row : rows) {
            if (row.createdAt != null && row.createdAt.length() >= 10) {
                LocalDate day = LocalDate.parse(row.createdAt.substring(0, 10));
                if (!day.isBefore(fromInclusive)) {
                    map.merge(day.toString(), 1L, Long::sum);
                }
            }
        }
        return map;
    }

    @Override
    public TaskDto getTask(String taskId) {
        return toDto(requireRow(taskId), RequestContext.requirePrincipal());
    }

    @Override
    public TaskDto urge(String taskId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        TaskDto current = toDto(requireRow(taskId), principal);
        if (!current.canUrge()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "当前节点不可催办");
        }
        Row row = requireRow(taskId);
        row.urgeCount += 1;
        row.lastUrgeAt = TimeFormats.DISPLAY.format(LocalDateTime.now());
        auditRecorder.record("urge", row.projectId, row.fileId, row.id, "催办 " + row.id, "success");
        TaskDto updated = toDto(row, principal);
        noticeRecorder.notifyReviewers(new NoticeCommand(
                "urge",
                "待审核催办",
                principal.displayName() + "催办" + updated.type() + "「" + updated.title()
                        + "」，请尽快审核。",
                updated.id(),
                updated.projectId(),
                updated.projectName(),
                updated.fileId(),
                updated.applyType(),
                principal.userId(),
                principal.displayName()
        ));
        return updated;
    }

    @Override
    public TaskDto retry(String taskId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        TaskDto current = toDto(requireRow(taskId), principal);
        if (!current.canRetry()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "当前状态不可重新提交");
        }
        Row row = requireRow(taskId);
        row.circStatus = "pending";
        row.dist = "none";
        row.deleted = false;
        row.reviewUser = "";
        row.comment = "";
        auditRecorder.record("resubmit", row.projectId, row.fileId, row.id, "重新提交 " + row.id, "success");
        return toDto(row, principal);
    }

    @Override
    public TaskDto withdraw(String taskId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        TaskDto current = toDto(requireRow(taskId), principal);
        if (!current.canWithdraw()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "仅未审核的提交可由发起人撤回");
        }
        Row row = requireRow(taskId);
        row.circStatus = "withdrawn";
        row.comment = "发起人撤回";
        auditRecorder.record("withdraw", row.projectId, row.fileId, row.id, "撤回 " + row.id, "success");
        return toDto(row, principal);
    }

    @Override
    public TaskDto deleteTask(String taskId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        Checks.requirePermission(principal, "review");
        TaskDto current = toDto(requireRow(taskId), principal);
        if (!current.canDelete()) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "当前状态不可删除");
        }
        Row row = requireRow(taskId);
        row.deleted = true;
        auditRecorder.record("delete_circulation", row.projectId, row.fileId, row.id, "删除 " + row.id, "success");
        return toDto(row, principal);
    }

    @Override
    public TaskDto createTask(CreateTaskRequest request) {
        throw new ApiException(ErrorCode.BAD_REQUEST, "请在项目管理或文件管理中新增提交");
    }

    @Override
    public TaskDto syncFromServer2(String taskId) {
        throw new ApiException(ErrorCode.BAD_REQUEST, "请到流转控制完成分发");
    }

    @Override
    public TaskDto submitForReview(String taskId) {
        return retry(taskId);
    }

    @Override
    public TaskDto cancelTask(String taskId) {
        return withdraw(taskId);
    }

    @Override
    public TaskResultDto downloadResult(String taskId) {
        RequestContext.requirePrincipal();
        Row row = requireRow(taskId);
        if (!row.outputReady) {
            throw new ApiException(ErrorCode.BAD_REQUEST, "处理结果尚未就绪");
        }
        auditRecorder.record("download_result", row.projectId, row.fileId, row.id,
                "领取结果索引 " + row.resultId, "success");
        return new TaskResultDto(row.id, row.resultId, "sha256:res4001demo", "proof:stub",
                "结果文件由服务器2只读接口提供，服务器1只保存结果索引、哈希和存证摘要。");
    }

    private Row requireRow(String taskId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        Row found = rows.stream()
                .filter(row -> row.id.equals(taskId))
                .findFirst()
                .orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND, "任务流程不存在"));
        DataScope.requireVisible(principal, found.applyUserId);
        return found;
    }

    private static TaskDto toDto(Row row, AccessPrincipal principal) {
        TaskDto base = TaskWorkflow.build(
                row.id, row.applyType, row.projectId, row.projectName, row.fileId, row.fileName,
                row.applyUserId, row.applyUser, row.reviewUser, row.circStatus, row.dist,
                row.comment, row.purpose, row.urgeCount, row.lastUrgeAt, row.createdAt, row.updatedAt,
                row.deleted, principal
        );
        if (row.resultId == null) {
            return base;
        }
        return new TaskDto(
                base.id(), base.applyType(), base.title(), base.projectId(), base.projectName(),
                base.fileId(), base.fileName(), base.applyUserId(), base.applyUser(), base.reviewUser(),
                base.status(), base.stage(), base.currentNode(), base.currentNodeLabel(), base.progress(),
                base.circulationStatus(), base.distributeStatus(), base.comment(), base.purpose(),
                base.urgeCount(), base.lastUrgeAt(), base.canUrge(), base.canRetry(),
                base.canWithdraw(), base.canDelete(), base.canDistribute(), base.nodes(),
                base.createdAt(), base.updatedAt(),
                base.type(), row.resultId, row.outputReady
        );
    }

    private static final class Row {
        private final String id;
        private final String applyType;
        private final String projectId;
        private final String projectName;
        private final String fileId;
        private final String fileName;
        private final String applyUserId;
        private final String applyUser;
        private String reviewUser;
        private String circStatus;
        private String dist;
        private String comment;
        private final String purpose;
        private int urgeCount;
        private String lastUrgeAt;
        private final String createdAt;
        private final String updatedAt;
        private boolean deleted;
        private final String resultId;
        private final boolean outputReady;

        private Row(String id, String applyType, String projectId, String projectName, String fileId, String fileName,
                    String applyUserId, String applyUser, String reviewUser, String circStatus, String dist,
                    String comment, String purpose, int urgeCount, String lastUrgeAt, String createdAt,
                    String updatedAt, boolean deleted, String resultId, boolean outputReady) {
            this.id = id;
            this.applyType = applyType;
            this.projectId = projectId;
            this.projectName = projectName;
            this.fileId = fileId;
            this.fileName = fileName;
            this.applyUserId = applyUserId;
            this.applyUser = applyUser;
            this.reviewUser = reviewUser;
            this.circStatus = circStatus;
            this.dist = dist;
            this.comment = comment;
            this.purpose = purpose;
            this.urgeCount = urgeCount;
            this.lastUrgeAt = lastUrgeAt;
            this.createdAt = createdAt;
            this.updatedAt = updatedAt;
            this.deleted = deleted;
            this.resultId = resultId;
            this.outputReady = outputReady;
        }
    }
}
