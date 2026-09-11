-- 普通员工账号：可新建项目、上传文件、发起自己的处理作业；不能审批、不能分发。
SET NAMES utf8mb4;

INSERT INTO sys_user (user_id, username, password, display_name, status)
SELECT 'u_zhangsan', 'zhangsan', 'zhangsan123', '张三', 1
WHERE NOT EXISTS (SELECT 1 FROM sys_user WHERE user_id = 'u_zhangsan' OR username = 'zhangsan');

INSERT INTO sys_user (user_id, username, password, display_name, status)
SELECT 'u_lisi', 'lisi', 'lisi123', '李四', 1
WHERE NOT EXISTS (SELECT 1 FROM sys_user WHERE user_id = 'u_lisi' OR username = 'lisi');

INSERT INTO sys_user_role (user_id, role_code)
SELECT 'u_zhangsan', 'operator'
WHERE NOT EXISTS (SELECT 1 FROM sys_user_role WHERE user_id = 'u_zhangsan');

INSERT INTO sys_user_role (user_id, role_code)
SELECT 'u_lisi', 'operator'
WHERE NOT EXISTS (SELECT 1 FROM sys_user_role WHERE user_id = 'u_lisi');
