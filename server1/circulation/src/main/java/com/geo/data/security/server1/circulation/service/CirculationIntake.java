package com.geo.data.security.server1.circulation.service;

/**
 * 业务侧提交审核：新建项目、上传文件时打开流转待办；
 * 已入库文件发起处理作业时沿用入库授权，不再重复审批/分发。
 */
public interface CirculationIntake {

    void openTicket(String applyType, String projectId, String fileId, String taskId, String purpose);

    void openInheritedDispatch(String applyType, String projectId, String fileId, String taskId, String purpose);
}
