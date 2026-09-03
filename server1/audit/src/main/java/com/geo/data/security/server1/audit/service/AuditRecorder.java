package com.geo.data.security.server1.audit.service;

import com.geo.data.security.server1.audit.model.AuditEventCommand;

/**
 * 业务事件产生与提交。各模块在登录/上传/项目/任务/审批后调用，不直接操作 ES 或链上私钥。
 */
public interface AuditRecorder {

    void record(AuditEventCommand command);

    default void record(String action, String projectId, String fileId, String taskId,
                        String detail, String resultStatus) {
        record(AuditEventCommand.of(action, projectId, fileId, taskId, detail, resultStatus));
    }
}
