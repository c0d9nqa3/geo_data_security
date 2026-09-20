package com.geo.data.security.server1.ingest.service;

import com.geo.data.security.server1.circulation.service.Server2TraceSnapshot;
import com.geo.data.security.server1.ingest.controller.dto.FileProvenanceDto;
import com.geo.data.security.server1.ingest.controller.dto.FileProvenanceEvidenceDto;
import com.geo.data.security.server1.ingest.controller.dto.FileProvenanceNodeDto;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class FileProvenanceAssembler {

    private static final Pattern TASK = Pattern.compile("(?:^|\\s)task=([A-Za-z0-9._-]+)");
    private static final Pattern RESULT = Pattern.compile("(?:^|\\s)result=([A-Za-z0-9._-]+)");
    private static final Pattern PATH = Pattern.compile("((?:[A-Za-z]:|V:)[\\\\/][^\\s]+|/[^\\s]+)");

    private FileProvenanceAssembler() {
    }

    record Circ(
            String status,
            String distributeStatus,
            String applyName,
            String reviewName,
            String comment,
            String createdAt,
            String updatedAt,
            String resultId
    ) {
    }

    record Ids(String taskId, String resultId, String sourcePath) {
        static Ids empty() {
            return new Ids("", "", "");
        }
    }

    static Ids parseComment(String comment) {
        if (comment == null || comment.isBlank()) {
            return Ids.empty();
        }
        return new Ids(match(TASK, comment), match(RESULT, comment), match(PATH, comment));
    }

    static String firstNonBlank(String... values) {
        if (values == null) {
            return "";
        }
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return "";
    }

    static FileProvenanceDto assemble(
            String fileId,
            String fileName,
            String projectId,
            String projectName,
            String fileStatus,
            String uploadedBy,
            String uploadedAt,
            String contentHash,
            Circ circ,
            Server2TraceSnapshot live,
            String taskId,
            String resultId,
            String sourcePath
    ) {
        Server2TraceSnapshot snap = live == null ? Server2TraceSnapshot.unavailable("") : live;
        String circStatus = circ == null ? "" : blank(circ.status());
        String dist = circ == null ? "" : blank(circ.distributeStatus());
        boolean dispatched = "dispatched".equals(dist) || "transferred".equals(blank(fileStatus));
        boolean distFailed = "failed".equals(dist);
        boolean rejected = "rejected".equals(circStatus);
        boolean withdrawn = "withdrawn".equals(circStatus);
        boolean approved = "approved".equals(circStatus) || dispatched || distFailed;

        String taskStatus = upper(snap.taskStatus());
        String resultStatus = upper(snap.resultStatus());
        boolean liveOk = snap.available();
        boolean taskFailed = contains(taskStatus, "FAILED", "ERROR");
        boolean taskRunning = contains(taskStatus, "RUNNING", "PROCESSING", "PENDING", "QUEUED", "UPLOADING");
        boolean taskDone = liveOk && (contains(taskStatus, "COMPLETED", "SUCCESS", "APPROVED", "DONE")
                || contains(resultStatus, "APPROVED", "COMPLETED", "SUCCESS")
                || Boolean.TRUE.equals(snap.verified())
                || Boolean.TRUE.equals(snap.onChain()));
        if (dispatched && liveOk && !taskFailed && !taskRunning && !taskStatus.isBlank()) {
            taskDone = taskDone || !contains(taskStatus, "FAILED", "ERROR");
        }

        List<FileProvenanceNodeDto> nodes = new ArrayList<>();
        nodes.add(node("upload", "上传入库", "done", uploadedBy, uploadedAt, "文件已进入服务器1"));

        if (circ == null) {
            nodes.add(node("review", "管理员审核", "waiting", "", "", "尚未生成审核单"));
        } else if (withdrawn) {
            nodes.add(node("review", "管理员审核", "skipped", circ.applyName(), circ.updatedAt(), "已撤回"));
        } else if (rejected) {
            nodes.add(node("review", "管理员审核", "rejected", circ.reviewName(), circ.updatedAt(),
                    firstNonBlank(circ.comment(), "审核未通过")));
        } else if (approved) {
            nodes.add(node("review", "管理员审核", "done", circ.reviewName(), circ.updatedAt(), "审核通过，允许分发"));
        } else {
            nodes.add(node("review", "管理员审核", "current", circ.applyName(), circ.createdAt(), "待管理员审核"));
        }

        if (distFailed) {
            nodes.add(node("dispatch", "分发到服务器2", "failed", circ == null ? "" : circ.applyName(),
                    circ == null ? "" : circ.updatedAt(), firstNonBlank(circ == null ? "" : circ.comment(), "分发失败")));
        } else if (dispatched) {
            nodes.add(node("dispatch", "分发到服务器2", "done", circ == null ? "" : circ.applyName(),
                    circ == null ? "" : circ.updatedAt(),
                    firstNonBlank(sourcePath, "已提交服务器2")));
        } else if (approved && !rejected && !withdrawn) {
            nodes.add(node("dispatch", "分发到服务器2", "current", "", "", "审核已通过，待向服务器2分发"));
        } else {
            nodes.add(node("dispatch", "分发到服务器2", "waiting", "", "", "审核通过后才能分发"));
        }

        if (distFailed || rejected || withdrawn) {
            nodes.add(node("parse", "解析落盘", "skipped", "", "", "未进入服务器2处理"));
            nodes.add(node("process", "安全处理", "skipped", "", "", "未进入服务器2处理"));
            nodes.add(node("approve_result", "结果审批", "skipped", "", "", "未进入服务器2处理"));
            nodes.add(node("chain", "上链存证", "skipped", "", "", "未进入服务器2处理"));
            nodes.add(node("verify", "溯源校验", "skipped", "", "", "未进入服务器2处理"));
        } else if (!dispatched) {
            nodes.add(node("parse", "解析落盘", "waiting", "", "", "分发后由服务器2解析"));
            nodes.add(node("process", "安全处理", "waiting", "", "", "分发后进行水印等安全处理"));
            nodes.add(node("approve_result", "结果审批", "waiting", "", "", "处理完成后审批结果"));
            nodes.add(node("chain", "上链存证", "waiting", "", "", "审批通过后写入区块链"));
            nodes.add(node("verify", "溯源校验", "waiting", "", "", "用哈希与链上凭证回验"));
        } else if (!liveOk) {
            String pending = firstNonBlank(snap.hint(), "已分发，正在查询服务器2处理进度");
            nodes.add(node("parse", "解析落盘", "current", "", "", pending));
            nodes.add(node("process", "安全处理", "waiting", "", "", "等待服务器2返回"));
            nodes.add(node("approve_result", "结果审批", "waiting", "", "", "等待服务器2返回"));
            nodes.add(node("chain", "上链存证", "waiting", "", "", "等待服务器2返回"));
            nodes.add(node("verify", "溯源校验", "waiting", "", "", "等待服务器2返回"));
        } else if (taskFailed) {
            nodes.add(node("parse", "解析落盘", blank(sourcePath).isEmpty() ? "failed" : "done",
                    "", snap.processedAt(), firstNonBlank(sourcePath, snap.hint(), "解析失败")));
            nodes.add(node("process", "安全处理", "failed", "", snap.processedAt(),
                    firstNonBlank(snap.hint(), "服务器2处理失败")));
            nodes.add(node("approve_result", "结果审批", "skipped", "", "", "处理失败，未审批"));
            nodes.add(node("chain", "上链存证", "skipped", "", "", "处理失败，未上链"));
            nodes.add(node("verify", "溯源校验", "skipped", "", "", "处理失败，未校验"));
        } else if (taskRunning && !taskDone) {
            boolean parsed = !blank(firstNonBlank(sourcePath, snap.sourcePath())).isEmpty();
            nodes.add(node("parse", "解析落盘", parsed ? "done" : "current", "", snap.processedAt(),
                    parsed ? firstNonBlank(sourcePath, snap.sourcePath()) : "服务器2正在解析"));
            nodes.add(node("process", "安全处理", "current", "", snap.processedAt(),
                    "服务器2处理中 " + firstNonBlank(taskStatus, resultStatus)));
            nodes.add(node("approve_result", "结果审批", "waiting", "", "", "处理完成后审批"));
            nodes.add(node("chain", "上链存证", "waiting", "", "", "审批后上链"));
            nodes.add(node("verify", "溯源校验", "waiting", "", "", "上链后回验"));
        } else {
            nodes.add(node("parse", "解析落盘", "done", "", snap.processedAt(),
                    firstNonBlank(sourcePath, snap.sourcePath(), "已在服务器2落盘")));
            nodes.add(node("process", "安全处理", "done", "", snap.processedAt(),
                    processRemark(snap)));
            if (contains(resultStatus, "APPROVED", "COMPLETED", "SUCCESS") || Boolean.TRUE.equals(snap.verified())) {
                nodes.add(node("approve_result", "结果审批", "done", "", snap.processedAt(),
                        firstNonBlank(resultStatus, "结果已审批")));
            } else if (contains(resultStatus, "REJECTED", "DENIED")) {
                nodes.add(node("approve_result", "结果审批", "rejected", "", snap.processedAt(), resultStatus));
            } else {
                nodes.add(node("approve_result", "结果审批", "current", "", "", "等待结果审批"));
            }
            if (Boolean.TRUE.equals(snap.onChain())) {
                nodes.add(node("chain", "上链存证", "done", "", snap.processedAt(),
                        chainRemark(snap)));
            } else if (contains(resultStatus, "APPROVED", "COMPLETED", "SUCCESS") || Boolean.TRUE.equals(snap.verified())) {
                nodes.add(node("chain", "上链存证", "current", "", "", "处理完成，待确认链上凭证"));
            } else {
                nodes.add(node("chain", "上链存证", "waiting", "", "", "审批通过后上链"));
            }
            if (Boolean.TRUE.equals(snap.verified())) {
                nodes.add(node("verify", "溯源校验", "done", "", snap.processedAt(), verifyRemark(snap)));
            } else if (Boolean.FALSE.equals(snap.verified())) {
                nodes.add(node("verify", "溯源校验", "failed", "", snap.processedAt(),
                        firstNonBlank(snap.method(), "校验未通过")));
            } else if (Boolean.TRUE.equals(snap.onChain())) {
                nodes.add(node("verify", "溯源校验", "current", "", "", "链上已有凭证，待回验"));
            } else {
                nodes.add(node("verify", "溯源校验", "waiting", "", "", "上链后回验哈希"));
            }
        }

        String currentKey = "upload";
        String currentLabel = "已上传";
        for (FileProvenanceNodeDto node : nodes) {
            if ("current".equals(node.state()) || "failed".equals(node.state()) || "rejected".equals(node.state())) {
                currentKey = node.key();
                currentLabel = node.label() + " · " + stateLabel(node.state());
                break;
            }
            if ("done".equals(node.state())) {
                currentKey = node.key();
                currentLabel = node.label() + " · 已完成";
            }
        }

        String liveHint;
        if (!dispatched) {
            liveHint = "当前只展示服务器1本地节点；向服务器2分发成功后会补上解析、处理、上链和校验。";
        } else if (liveOk) {
            liveHint = "处理、上链、校验节点来自服务器2实时查询。";
        } else {
            liveHint = firstNonBlank(snap.hint(), "已分发，但服务器2溯源暂不可用，先展示本地分发记录。");
        }

        FileProvenanceEvidenceDto evidence = new FileProvenanceEvidenceDto(
                firstNonBlank(taskId, snap.taskId()),
                firstNonBlank(resultId, snap.resultId()),
                firstNonBlank(sourcePath, snap.sourcePath()),
                firstNonBlank(contentHash, snap.sourceHash()),
                blank(snap.outputHash()),
                blank(snap.chainTx()),
                blank(snap.chainBlock()),
                snap.onChain(),
                snap.verified(),
                blank(snap.method()),
                snap.filesProcessed(),
                snap.matched(),
                blank(snap.watermark()),
                firstNonBlank(taskStatus, resultStatus)
        );
        return new FileProvenanceDto(
                fileId, fileName, projectId, projectName, blank(fileStatus),
                currentKey, currentLabel, liveOk && dispatched, liveHint, nodes, evidence);
    }

    private static FileProvenanceNodeDto node(String key, String label, String state,
                                              String actor, String time, String remark) {
        return new FileProvenanceNodeDto(key, label, state, blank(actor), blank(time), blank(remark));
    }

    private static String processRemark(Server2TraceSnapshot snap) {
        if (snap.filesProcessed() != null && snap.matched() != null) {
            return "已处理 " + snap.filesProcessed() + " 个文件，匹配 " + snap.matched();
        }
        if (snap.filesProcessed() != null) {
            return "已处理 " + snap.filesProcessed() + " 个文件";
        }
        return firstNonBlank(snap.method(), "服务器2安全处理完成");
    }

    private static String chainRemark(Server2TraceSnapshot snap) {
        String block = blank(snap.chainBlock());
        if (!block.isEmpty()) {
            return "已写入区块链，区块 " + block;
        }
        return "已写入区块链";
    }

    private static String verifyRemark(Server2TraceSnapshot snap) {
        String method = blank(snap.method());
        if (snap.filesProcessed() != null && snap.matched() != null) {
            return (method.isEmpty() ? "校验通过" : method) + " · " + snap.matched() + "/" + snap.filesProcessed();
        }
        return method.isEmpty() ? "哈希与链上凭证校验通过" : method + " 校验通过";
    }

    private static String stateLabel(String state) {
        return switch (state) {
            case "done" -> "已完成";
            case "current" -> "进行中";
            case "failed" -> "失败";
            case "rejected" -> "已驳回";
            case "skipped" -> "已跳过";
            default -> "未到达";
        };
    }

    private static String match(Pattern pattern, String text) {
        Matcher matcher = pattern.matcher(text);
        return matcher.find() ? matcher.group(1) : "";
    }

    private static boolean contains(String value, String... tokens) {
        if (value == null || value.isBlank()) {
            return false;
        }
        for (String token : tokens) {
            if (value.contains(token)) {
                return true;
            }
        }
        return false;
    }

    private static String upper(String value) {
        return blank(value).toUpperCase(Locale.ROOT);
    }

    private static String blank(String value) {
        return value == null ? "" : value.trim();
    }
}
