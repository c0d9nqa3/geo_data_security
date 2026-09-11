package com.geo.data.security.server1.task.service;

final class TaskStages {

    private TaskStages() {
    }

    static String resolve(String status, int progress, String circStatus, String dist, String resultId) {
        if ("rejected".equals(status) || "rejected".equals(circStatus)) {
            return "rejected";
        }
        if ("failed".equals(status)) {
            return "failed";
        }
        boolean hasResult = resultId != null && !resultId.isBlank();
        if (hasResult && (progress >= 100 || "approved".equals(status))) {
            return "completed";
        }
        if ("dispatched".equals(dist) || "running".equals(status)) {
            return "processing";
        }
        if ("approved".equals(circStatus) && !"dispatched".equals(dist)) {
            return "awaiting_dispatch";
        }
        if ("pending".equals(circStatus)) {
            return "awaiting_review";
        }
        if ("waiting_review".equals(status)) {
            return "awaiting_review";
        }
        if ("queued".equals(status) && (circStatus == null || circStatus.isBlank())) {
            return "stranded";
        }
        if ("queued".equals(status)) {
            return "queued";
        }
        return status == null ? "queued" : status;
    }
}
