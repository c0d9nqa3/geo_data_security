-- 修复早期错误编码写入的中文（字面量 '?' / HEX 3F）。
-- 库本身已是 utf8mb4；本脚本只改已被替换成问号的业务展示字段。
SET NAMES utf8mb4;

UPDATE sys_user SET display_name = '系统管理员' WHERE user_id = 'u_admin';
UPDATE sys_user SET display_name = '业务操作员' WHERE user_id = 'u_operator';

UPDATE sys_role SET role_name = '系统管理员' WHERE role_code = 'admin';
UPDATE sys_role SET role_name = '业务操作员' WHERE role_code = 'operator';
UPDATE sys_role SET role_name = '审计员' WHERE role_code = 'auditor';
UPDATE sys_role SET role_name = '只读用户' WHERE role_code = 'viewer';

UPDATE sys_permission SET perm_name = '数据上传' WHERE perm_code = 'upload';
UPDATE sys_permission SET perm_name = '项目管理' WHERE perm_code = 'project';
UPDATE sys_permission SET perm_name = '任务提交与查询' WHERE perm_code = 'task';
UPDATE sys_permission SET perm_name = '审核审批' WHERE perm_code = 'review';
UPDATE sys_permission SET perm_name = '结果下载只读接口' WHERE perm_code = 'download';
UPDATE sys_permission SET perm_name = '追溯查询' WHERE perm_code = 'trace';
UPDATE sys_permission SET perm_name = '审计查看' WHERE perm_code = 'audit';

UPDATE biz_project
SET project_name = '城区正射影像库',
    description = '城区正射影像采集与水印处理项目'
WHERE project_id = 'prj_1001';

UPDATE biz_project
SET project_name = '河道矢量数据库',
    description = '河道矢量 SHP/GeoJSON 导入处理'
WHERE project_id = 'prj_1002';

UPDATE biz_project
SET project_name = '倾斜摄影模型库',
    description = '城区 OSGB 倾斜摄影三维模型库'
WHERE project_id = 'prj_1003';

UPDATE biz_project
SET project_name = '接口联调测试项目',
    description = 'API联调'
WHERE project_id = 'prj_1788405861089';

UPDATE biz_project
SET project_name = '界面测试项目B'
WHERE project_id = 'prj_1788406239226';

UPDATE biz_project
SET project_name = '正射影像项目A',
    description = '正射影像'
WHERE project_id = 'prj_1788423084091';

UPDATE biz_file SET file_name = '文档 1.txt' WHERE file_id = 'file_1788426401657';

UPDATE biz_task SET task_type = 'GeoTIFF 水印' WHERE task_id = 'task_3001';
UPDATE biz_task SET task_type = '矢量水印' WHERE task_id = 'task_3002';
UPDATE biz_task SET task_type = 'OSGB 水印' WHERE task_id = 'task_3003';
UPDATE biz_task SET task_type = 'GeoTIFF 水印' WHERE task_type LIKE 'GeoTIFF %' AND task_type LIKE '%?%';
UPDATE biz_task SET task_type = 'OSGB 水印' WHERE task_type LIKE 'OSGB %' AND task_type LIKE '%?%';

UPDATE biz_circulation SET purpose = '提交任务审核' WHERE circulation_id = 'cir_5001';
UPDATE biz_circulation SET purpose = '河道矢量成果输出' WHERE circulation_id = 'cir_5002';
UPDATE biz_circulation SET purpose = '新建项目审核：正射影像项目A' WHERE circulation_id = 'cir_906ceabbdcae';
UPDATE biz_circulation SET purpose = '上传文件审核：demo_upload_tile.tif' WHERE circulation_id = 'cir_81383b2cd73b';
UPDATE biz_circulation SET purpose = '上传文件审核：文档 1.txt' WHERE circulation_id = 'cir_efefd57ab581';
UPDATE biz_circulation SET purpose = '提交任务审核：GeoTIFF 水印'
WHERE apply_type = 'task' AND purpose LIKE '%GeoTIFF%';

UPDATE biz_circulation SET comment_text = '审核通过'
WHERE status = 'approved' AND comment_text REGEXP '^[?]+$';
UPDATE biz_circulation SET comment_text = '审核拒绝'
WHERE status = 'rejected' AND comment_text REGEXP '^[?]+$';

UPDATE biz_audit_event a
INNER JOIN sys_user u ON u.user_id = a.actor_user_id
SET a.actor_name = u.display_name
WHERE a.actor_name LIKE '%?%';
