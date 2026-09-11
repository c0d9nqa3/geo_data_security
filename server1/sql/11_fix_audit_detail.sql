-- 修复审计详情/操作人被写成字面量 '?' 的历史数据。
SET NAMES utf8mb4;

UPDATE biz_audit_event
SET actor_name = '系统'
WHERE actor_name LIKE '%?%';

UPDATE biz_audit_event a
LEFT JOIN biz_file f ON f.file_id = a.file_id
SET a.detail = CONCAT('上传 ', COALESCE(f.file_name, ''))
WHERE a.action = 'upload' AND a.detail LIKE '%?%';

UPDATE biz_audit_event a
LEFT JOIN biz_project p ON p.project_id = a.project_id
SET a.detail = CONCAT('创建项目 ', COALESCE(p.project_code, ''), '（', COALESCE(p.project_name, ''), '）')
WHERE a.action = 'create_project' AND a.detail LIKE '%?%';

UPDATE biz_audit_event a
LEFT JOIN biz_task t ON t.task_id = a.task_id
SET a.detail = CONCAT('提交任务 ', COALESCE(a.task_id, ''), '（', COALESCE(t.task_type, ''), '）')
WHERE a.action = 'submit_task' AND a.detail LIKE '%?%';

UPDATE biz_audit_event a
LEFT JOIN biz_circulation c ON c.circulation_id = SUBSTRING_INDEX(a.detail, ' ', -1)
SET a.detail = CONCAT(
    '提交',
    CASE COALESCE(c.apply_type, CASE WHEN a.task_id IS NOT NULL THEN 'task' WHEN a.file_id IS NOT NULL THEN 'file' ELSE 'project' END)
        WHEN 'project' THEN '新建项目'
        WHEN 'file' THEN '上传文件'
        ELSE '提交任务'
    END,
    '待办 ',
    SUBSTRING_INDEX(a.detail, ' ', -1)
)
WHERE a.action = 'apply_circulation' AND a.detail LIKE '%?%';

UPDATE biz_audit_event a
LEFT JOIN biz_circulation c ON c.circulation_id = SUBSTRING_INDEX(a.detail, ' ', -1)
SET a.detail = CONCAT(
    '通过',
    CASE COALESCE(c.apply_type, CASE WHEN a.task_id IS NOT NULL THEN 'task' WHEN a.file_id IS NOT NULL THEN 'file' ELSE 'project' END)
        WHEN 'project' THEN '新建项目'
        WHEN 'file' THEN '上传文件'
        ELSE '提交任务'
    END,
    ' ',
    SUBSTRING_INDEX(a.detail, ' ', -1)
)
WHERE a.action = 'approve' AND a.detail LIKE '%?%';

UPDATE biz_audit_event a
LEFT JOIN biz_circulation c ON c.circulation_id = SUBSTRING_INDEX(a.detail, ' ', -1)
SET a.detail = CONCAT(
    '驳回',
    CASE COALESCE(c.apply_type, CASE WHEN a.task_id IS NOT NULL THEN 'task' WHEN a.file_id IS NOT NULL THEN 'file' ELSE 'project' END)
        WHEN 'project' THEN '新建项目'
        WHEN 'file' THEN '上传文件'
        ELSE '提交任务'
    END,
    ' ',
    SUBSTRING_INDEX(a.detail, ' ', -1)
)
WHERE a.action = 'reject' AND a.detail LIKE '%?%';

UPDATE biz_audit_event a
LEFT JOIN biz_circulation c ON c.circulation_id = SUBSTRING_INDEX(a.detail, ' ', -1)
SET a.detail = CONCAT(
    '向服务器2提交',
    CASE COALESCE(c.apply_type, CASE WHEN a.task_id IS NOT NULL THEN 'task' WHEN a.file_id IS NOT NULL THEN 'file' ELSE 'project' END)
        WHEN 'project' THEN '新建项目'
        WHEN 'file' THEN '上传文件'
        ELSE '提交任务'
    END,
    '授权 ',
    SUBSTRING_INDEX(a.detail, ' ', -1)
)
WHERE a.action = 'distribute' AND a.detail LIKE '%?%';

UPDATE biz_audit_event
SET detail = CONCAT('逻辑删除流转单 ', SUBSTRING_INDEX(detail, ' ', -1))
WHERE action = 'delete_circulation' AND detail LIKE '%?%';

UPDATE biz_audit_event
SET detail = '下载处理结果'
WHERE action = 'download_result' AND detail LIKE '%?%';

UPDATE biz_audit_event
SET detail = '追溯查询'
WHERE action = 'query_trace' AND detail LIKE '%?%';
