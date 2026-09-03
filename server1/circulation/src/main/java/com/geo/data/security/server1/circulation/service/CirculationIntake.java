package com.geo.data.security.server1.circulation.service;

/**
 * 业务侧提交审核：新建项目、上传文件、提交任务时自动打开流转待办。
 */
public interface CirculationIntake {

    void openTicket(String applyType, String projectId, String fileId, String taskId, String purpose);
}
