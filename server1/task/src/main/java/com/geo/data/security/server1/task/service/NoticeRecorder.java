package com.geo.data.security.server1.task.service;

/**
 * 写站内消息。催办时通知审核人。
 */
public interface NoticeRecorder {

    void notifyReviewers(NoticeCommand command);
}
