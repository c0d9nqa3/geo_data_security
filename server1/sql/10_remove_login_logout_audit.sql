-- 审计追溯不记录登录/退出。清理已写入的会话类事件。
DELETE FROM biz_audit_event WHERE action IN ('login', 'logout');
