package com.geo.data.security.server1.task.service;

import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.common.support.Checks;
import com.geo.data.security.server1.common.support.DataScope;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.task.controller.dto.NoticeDto;
import com.geo.data.security.server1.task.controller.dto.NoticeUnreadDto;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "stub")
public class StubNoticeService implements NoticeService, NoticeRecorder {

    private static final List<String> REVIEWER_IDS = List.of("u_admin");

    private final List<Row> rows = new CopyOnWriteArrayList<>();

    @Override
    public PageDto<NoticeDto> listNotices(Integer page, Integer pageSize) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        List<NoticeDto> mine = mine(principal);
        return PageDto.slice(mine, page, pageSize);
    }

    @Override
    public NoticeUnreadDto unreadCount() {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        long unread = mine(principal).stream().filter(item -> !item.read()).count();
        return new NoticeUnreadDto(unread);
    }

    @Override
    public NoticeDto markRead(String noticeId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        String id = Checks.requireText(noticeId, "消息不存在");
        for (Row row : rows) {
            if (row.id.equals(id) && principal.userId().equals(row.recipientUserId)) {
                row.read = true;
                return toDto(row);
            }
        }
        throw new ApiException(ErrorCode.NOT_FOUND, "消息不存在");
    }

    @Override
    public NoticeUnreadDto markAllRead() {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        for (Row row : rows) {
            if (principal.userId().equals(row.recipientUserId)) {
                row.read = true;
            }
        }
        return unreadCount();
    }

    @Override
    public void notifyReviewers(NoticeCommand command) {
        if (command == null) {
            return;
        }
        String now = TimeFormats.DISPLAY.format(LocalDateTime.now());
        for (String recipientId : REVIEWER_IDS) {
            if (recipientId.equals(command.senderUserId())) {
                continue;
            }
            rows.add(0, new Row(
                    "ntc_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8),
                    command.type(),
                    command.title(),
                    command.content(),
                    command.circulationId(),
                    command.projectId(),
                    command.projectName(),
                    command.fileId(),
                    command.applyType(),
                    command.senderUserId(),
                    command.senderName(),
                    recipientId,
                    false,
                    now
            ));
        }
    }

    private List<NoticeDto> mine(AccessPrincipal principal) {
        if (!DataScope.canSeeAll(principal) && !REVIEWER_IDS.contains(principal.userId())) {
            return List.of();
        }
        List<NoticeDto> mine = new ArrayList<>();
        for (Row row : rows) {
            if (principal.userId().equals(row.recipientUserId)) {
                mine.add(toDto(row));
            }
        }
        return mine;
    }

    private static NoticeDto toDto(Row row) {
        String senderName = TimeFormats.nullToEmpty(row.senderName);
        if (senderName.isBlank()) {
            senderName = "u_zhangsan".equals(row.senderUserId) ? "张三"
                    : "u_lisi".equals(row.senderUserId) ? "李四"
                    : "u_operator".equals(row.senderUserId) ? "业务操作员"
                    : "系统管理员";
        }
        return new NoticeDto(
                row.id,
                TimeFormats.nullToEmpty(row.type),
                TimeFormats.nullToEmpty(row.title),
                TimeFormats.nullToEmpty(row.content),
                row.circulationId,
                row.projectId,
                TimeFormats.nullToEmpty(row.projectName),
                row.fileId,
                row.applyType,
                TaskWorkflow.typeLabel(row.applyType),
                row.senderUserId,
                senderName,
                row.read,
                row.createdAt
        );
    }

    private static final class Row {
        private final String id;
        private final String type;
        private final String title;
        private final String content;
        private final String circulationId;
        private final String projectId;
        private final String projectName;
        private final String fileId;
        private final String applyType;
        private final String senderUserId;
        private final String senderName;
        private final String recipientUserId;
        private boolean read;
        private final String createdAt;

        private Row(String id, String type, String title, String content, String circulationId,
                    String projectId, String projectName, String fileId, String applyType,
                    String senderUserId, String senderName, String recipientUserId, boolean read, String createdAt) {
            this.id = id;
            this.type = type;
            this.title = title;
            this.content = content;
            this.circulationId = circulationId;
            this.projectId = projectId;
            this.projectName = projectName;
            this.fileId = fileId;
            this.applyType = applyType;
            this.senderUserId = senderUserId;
            this.senderName = senderName;
            this.recipientUserId = recipientUserId;
            this.read = read;
            this.createdAt = createdAt;
        }
    }
}
