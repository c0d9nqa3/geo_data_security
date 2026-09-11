package com.geo.data.security.server1.task.service;

import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.support.DataScope;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.task.controller.dto.TaskDto;
import com.geo.data.security.server1.task.controller.dto.TaskNodeDto;

import java.util.List;

final class TaskWorkflow {

    private TaskWorkflow() {
    }

    static TaskDto build(
            String id,
            String applyType,
            String projectId,
            String projectName,
            String fileId,
            String fileName,
            String applyUserId,
            String applyUser,
            String reviewUser,
            String circStatus,
            String distributeStatus,
            String comment,
            String purpose,
            int urgeCount,
            String lastUrgeAt,
            String createdAt,
            String updatedAt,
            boolean deleted,
            AccessPrincipal principal
    ) {
        String type = typeLabel(applyType);
        String title = titleOf(type, projectName, fileName, purpose, id);
        String dist = TimeFormats.nullToEmpty(distributeStatus);
        String status;
        String node;
        String nodeLabel;
        int progress;
        if (deleted) {
            status = "deleted";
            node = "submit";
            nodeLabel = "已删除，流转控制不再显示";
            progress = 0;
        } else if ("withdrawn".equals(circStatus)) {
            status = "withdrawn";
            node = "submit";
            nodeLabel = "已撤回，流转控制不再显示";
            progress = 20;
        } else if ("rejected".equals(circStatus)) {
            status = "rejected";
            node = "review";
            nodeLabel = "已驳回，流程终止";
            progress = 50;
        } else if ("failed".equals(dist)) {
            status = "failed";
            node = "distribute";
            nodeLabel = "分发失败";
            progress = 66;
        } else if ("dispatched".equals(dist)) {
            status = "completed";
            node = "done";
            nodeLabel = "已完成";
            progress = 100;
        } else if ("approved".equals(circStatus)) {
            status = "distributing";
            node = "distribute";
            nodeLabel = "待分发授权";
            progress = 66;
        } else {
            status = "pending";
            node = "review";
            nodeLabel = "待管理员审核";
            progress = 33;
        }
        boolean owner = DataScope.isOwner(principal, applyUserId);
        boolean admin = DataScope.canSeeAll(principal);
        boolean canUrge = owner && "pending".equals(status);
        boolean canRetry = (owner || admin)
                && ("rejected".equals(status) || "failed".equals(status) || "withdrawn".equals(status));
        boolean canWithdraw = owner && "pending".equals(status);
        boolean canDelete = admin && !"deleted".equals(status) && !"completed".equals(status);
        boolean canDistribute = (owner || admin)
                && "approved".equals(circStatus)
                && !"dispatched".equals(dist)
                && !deleted;
        List<TaskNodeDto> nodes = nodesOf(circStatus, dist, deleted, applyUser, reviewUser,
                comment, purpose, createdAt, updatedAt);
        return new TaskDto(
                id, applyType, title, projectId, projectName, fileId, fileName,
                applyUserId, applyUser, reviewUser, status, node, node, nodeLabel, progress,
                TimeFormats.nullToEmpty(circStatus), dist, TimeFormats.nullToEmpty(comment),
                TimeFormats.nullToEmpty(purpose), urgeCount, TimeFormats.nullToEmpty(lastUrgeAt),
                canUrge, canRetry, canWithdraw, canDelete, canDistribute, nodes, createdAt, updatedAt, type, null, false
        );
    }

    static String typeLabel(String applyType) {
        if ("project".equals(applyType)) {
            return "新建项目";
        }
        if ("file".equals(applyType)) {
            return "上传文件";
        }
        return "处理作业";
    }

    private static String titleOf(String type, String projectName, String fileName, String purpose, String id) {
        if (fileName != null && !fileName.isBlank()) {
            return fileName;
        }
        if (projectName != null && !projectName.isBlank()) {
            return projectName;
        }
        if (purpose != null && !purpose.isBlank()) {
            return purpose;
        }
        return id;
    }

    private static List<TaskNodeDto> nodesOf(String circStatus, String dist, boolean deleted,
                                             String applyUser, String reviewUser, String comment,
                                             String purpose, String createdAt, String updatedAt) {
        if (deleted) {
            return List.of(
                    new TaskNodeDto("submit", "提交申请", "done", applyUser, createdAt, purpose),
                    new TaskNodeDto("review", "管理员审核", "skipped", "", "", "已删除，未再审核"),
                    new TaskNodeDto("distribute", "分发授权", "skipped", "", "", "已从流转控制移除"),
                    new TaskNodeDto("done", "完成", "skipped", "", updatedAt, "任务管理保留已删除记录")
            );
        }
        if ("withdrawn".equals(circStatus)) {
            return List.of(
                    new TaskNodeDto("submit", "提交申请", "done", applyUser, createdAt, purpose),
                    new TaskNodeDto("review", "管理员审核", "skipped", applyUser, updatedAt, "发起人已撤回，审核未开始"),
                    new TaskNodeDto("distribute", "分发授权", "skipped", "", "", "撤回后不再分发"),
                    new TaskNodeDto("done", "完成", "skipped", "", updatedAt, "流程已撤回")
            );
        }
        return List.of(
                new TaskNodeDto("submit", "提交申请", "done", applyUser, createdAt,
                        TimeFormats.nullToEmpty(purpose)),
                reviewNode(circStatus, reviewUser, comment, createdAt, updatedAt),
                distributeNode(circStatus, dist, reviewUser, updatedAt, comment),
                doneNode(circStatus, dist, updatedAt)
        );
    }

    private static TaskNodeDto reviewNode(String circStatus, String reviewUser,
                                          String comment, String createdAt, String updatedAt) {
        if ("rejected".equals(circStatus)) {
            return new TaskNodeDto("review", "管理员审核", "rejected",
                    emptyTo(reviewUser, "管理员"), updatedAt,
                    emptyTo(comment, "审核拒绝，流程终止"));
        }
        if ("approved".equals(circStatus)) {
            return new TaskNodeDto("review", "管理员审核", "done",
                    emptyTo(reviewUser, "管理员"), updatedAt,
                    emptyTo(comment, "审核通过"));
        }
        return new TaskNodeDto("review", "管理员审核", "current",
                "待管理员处理", createdAt, "未审核，发起人可催办或撤回；审核通过后才能分发");
    }

    private static TaskNodeDto distributeNode(String circStatus, String dist, String reviewUser,
                                              String updatedAt, String comment) {
        if ("rejected".equals(circStatus)) {
            return new TaskNodeDto("distribute", "分发授权", "skipped", "", "", "流程已终止，未进入分发");
        }
        if ("failed".equals(dist)) {
            return new TaskNodeDto("distribute", "分发授权", "failed",
                    emptyTo(reviewUser, "管理员"), updatedAt,
                    emptyTo(comment, "分发失败，可通过后再次发起流转"));
        }
        if ("dispatched".equals(dist)) {
            return new TaskNodeDto("distribute", "分发授权", "done",
                    emptyTo(reviewUser, "管理员"), updatedAt, "已向服务器2提交授权");
        }
        if ("approved".equals(circStatus)) {
            return new TaskNodeDto("distribute", "分发授权", "current",
                    "待提交人分发", "", "审核已通过，提交人可到流转控制向服务器2分发");
        }
        return new TaskNodeDto("distribute", "分发授权", "waiting", "", "", "待审核通过后进入");
    }

    private static TaskNodeDto doneNode(String circStatus, String dist, String updatedAt) {
        if ("rejected".equals(circStatus)) {
            return new TaskNodeDto("done", "完成", "skipped", "", "", "已终止");
        }
        if ("dispatched".equals(dist)) {
            return new TaskNodeDto("done", "完成", "done", "", updatedAt, "节点走完");
        }
        if ("failed".equals(dist)) {
            return new TaskNodeDto("done", "完成", "waiting", "", "", "分发成功后完成");
        }
        return new TaskNodeDto("done", "完成", "waiting", "", "", "尚未到达");
    }

    private static String emptyTo(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }
}
