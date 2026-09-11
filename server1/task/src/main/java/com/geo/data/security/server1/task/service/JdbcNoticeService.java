package com.geo.data.security.server1.task.service;

import com.geo.data.security.server1.common.context.AccessPrincipal;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiException;
import com.geo.data.security.server1.common.error.ErrorCode;
import com.geo.data.security.server1.common.support.Checks;
import com.geo.data.security.server1.common.support.TimeFormats;
import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.task.controller.dto.NoticeDto;
import com.geo.data.security.server1.task.controller.dto.NoticeUnreadDto;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "jdbc", matchIfMissing = true)
public class JdbcNoticeService implements NoticeService, NoticeRecorder {

    private static final String LIST_SQL = """
            SELECT n.notice_id, n.notice_type, n.title, n.content, n.circulation_id, n.project_id,
                   COALESCE(n.project_name, '') AS project_name, n.file_id, n.apply_type, n.sender_user_id,
                   COALESCE(n.sender_name, n.sender_user_id, '') AS sender_name,
                   n.read_flag, n.created_at
            FROM biz_notice n
            """;

    private final JdbcTemplate jdbc;

    public JdbcNoticeService(JdbcTemplate jdbcTemplate) {
        this.jdbc = jdbcTemplate;
        ensureTable();
    }

    @Override
    public PageDto<NoticeDto> listNotices(Integer page, Integer pageSize) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        Long total = jdbc.queryForObject(
                "SELECT COUNT(*) FROM biz_notice WHERE recipient_user_id = ?",
                Long.class,
                principal.userId()
        );
        long count = total == null ? 0 : total;
        int size = PageDto.normalizeSize(pageSize);
        int pages = PageDto.totalPages(count, size);
        int current = PageDto.normalizePage(page, pages);
        int offset = (current - 1) * size;
        List<NoticeDto> items = jdbc.query(
                LIST_SQL + " WHERE n.recipient_user_id = ? ORDER BY n.created_at DESC, n.id DESC LIMIT ?, ?",
                this::mapNotice,
                principal.userId(), offset, size
        );
        return PageDto.of(items, count, current, size);
    }

    @Override
    public NoticeUnreadDto unreadCount() {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        Long total = jdbc.queryForObject(
                "SELECT COUNT(*) FROM biz_notice WHERE recipient_user_id = ? AND read_flag = 0",
                Long.class,
                principal.userId()
        );
        return new NoticeUnreadDto(total == null ? 0 : total);
    }

    @Override
    @Transactional
    public NoticeDto markRead(String noticeId) {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        String id = Checks.requireText(noticeId, "消息不存在");
        int updated = jdbc.update(
                "UPDATE biz_notice SET read_flag = 1 WHERE notice_id = ? AND recipient_user_id = ?",
                id, principal.userId()
        );
        if (updated == 0) {
            throw new ApiException(ErrorCode.NOT_FOUND, "消息不存在");
        }
        return requireOwn(id, principal.userId());
    }

    @Override
    @Transactional
    public NoticeUnreadDto markAllRead() {
        AccessPrincipal principal = RequestContext.requirePrincipal();
        jdbc.update(
                "UPDATE biz_notice SET read_flag = 1 WHERE recipient_user_id = ? AND read_flag = 0",
                principal.userId()
        );
        return unreadCount();
    }

    @Override
    @Transactional
    public void notifyReviewers(NoticeCommand command) {
        if (command == null) {
            return;
        }
        List<String> reviewers = jdbc.queryForList(
                """
                SELECT DISTINCT u.user_id
                FROM sys_user u
                INNER JOIN sys_user_role ur ON ur.user_id = u.user_id
                LEFT JOIN sys_role_permission rp ON rp.role_code = ur.role_code
                WHERE COALESCE(u.status, 1) = 1
                  AND (rp.perm_code = 'review' OR ur.role_code = 'admin' OR u.user_id = 'u_admin')
                """,
                String.class
        );
        LocalDateTime now = LocalDateTime.now();
        Timestamp ts = Timestamp.valueOf(now);
        for (String recipientId : reviewers) {
            if (recipientId == null || recipientId.equals(command.senderUserId())) {
                continue;
            }
            String noticeId = "ntc_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
            jdbc.update(
                    """
                    INSERT INTO biz_notice
                      (notice_id, notice_type, title, content, circulation_id, project_id, project_name, file_id,
                       apply_type, sender_user_id, sender_name, recipient_user_id, read_flag, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                    """,
                    noticeId,
                    TimeFormats.nullToEmpty(command.type()),
                    TimeFormats.nullToEmpty(command.title()),
                    TimeFormats.nullToEmpty(command.content()),
                    command.circulationId(),
                    command.projectId(),
                    TimeFormats.nullToEmpty(command.projectName()),
                    command.fileId(),
                    command.applyType(),
                    command.senderUserId(),
                    TimeFormats.nullToEmpty(command.senderName()),
                    recipientId,
                    ts
            );
        }
    }

    private NoticeDto requireOwn(String noticeId, String recipientUserId) {
        List<NoticeDto> found = jdbc.query(
                LIST_SQL + " WHERE n.notice_id = ? AND n.recipient_user_id = ? LIMIT 1",
                this::mapNotice,
                noticeId, recipientUserId
        );
        if (found.isEmpty()) {
            throw new ApiException(ErrorCode.NOT_FOUND, "消息不存在");
        }
        return found.get(0);
    }

    private NoticeDto mapNotice(java.sql.ResultSet rs, int i) throws java.sql.SQLException {
        String applyType = TimeFormats.nullToEmpty(rs.getString("apply_type"));
        return new NoticeDto(
                rs.getString("notice_id"),
                TimeFormats.nullToEmpty(rs.getString("notice_type")),
                TimeFormats.nullToEmpty(rs.getString("title")),
                TimeFormats.nullToEmpty(rs.getString("content")),
                rs.getString("circulation_id"),
                rs.getString("project_id"),
                TimeFormats.nullToEmpty(rs.getString("project_name")),
                rs.getString("file_id"),
                applyType,
                TaskWorkflow.typeLabel(applyType),
                rs.getString("sender_user_id"),
                TimeFormats.nullToEmpty(rs.getString("sender_name")),
                rs.getInt("read_flag") == 1,
                TimeFormats.format(rs.getTimestamp("created_at"))
        );
    }

    private void ensureTable() {
        jdbc.execute(
                """
                CREATE TABLE IF NOT EXISTS biz_notice (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  notice_id VARCHAR(64) NOT NULL,
                  notice_type VARCHAR(32) NOT NULL,
                  title VARCHAR(200) NOT NULL,
                  content VARCHAR(1000) NOT NULL DEFAULT '',
                  circulation_id VARCHAR(64) NULL,
                  project_id VARCHAR(64) NULL,
                  project_name VARCHAR(200) NULL,
                  file_id VARCHAR(64) NULL,
                  apply_type VARCHAR(32) NULL,
                  sender_user_id VARCHAR(64) NULL,
                  sender_name VARCHAR(128) NULL,
                  recipient_user_id VARCHAR(64) NOT NULL,
                  read_flag TINYINT NOT NULL DEFAULT 0,
                  created_at DATETIME NOT NULL,
                  PRIMARY KEY (id),
                  UNIQUE KEY uk_notice_id (notice_id),
                  KEY idx_notice_recipient (recipient_user_id, read_flag, created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
                """
        );
        jdbc.execute("ALTER TABLE biz_notice CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci");
        addColumnIfMissing("project_name", "VARCHAR(200) NULL");
        addColumnIfMissing("sender_name", "VARCHAR(128) NULL");
        try {
            jdbc.update(
                    """
                    UPDATE biz_notice n
                    LEFT JOIN sys_user su ON su.user_id = n.sender_user_id
                    SET n.sender_name = su.display_name
                    WHERE (n.sender_name IS NULL OR n.sender_name = '') AND su.display_name IS NOT NULL
                    """
            );
            jdbc.update(
                    """
                    UPDATE biz_notice n
                    LEFT JOIN biz_project p ON p.project_id = n.project_id
                    SET n.project_name = p.project_name
                    WHERE (n.project_name IS NULL OR n.project_name = '') AND p.project_name IS NOT NULL
                    """
            );
        } catch (Exception ignored) {
            // 旧数据补全失败不影响列表查询
        }
    }

    private void addColumnIfMissing(String column, String spec) {
        Integer n = jdbc.queryForObject(
                """
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'biz_notice' AND COLUMN_NAME = ?
                """,
                Integer.class, column
        );
        if (n == null || n == 0) {
            jdbc.execute("ALTER TABLE biz_notice ADD COLUMN " + column + " " + spec);
        }
    }
}
