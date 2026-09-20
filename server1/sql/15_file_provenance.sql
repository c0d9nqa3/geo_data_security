-- 文件溯源：把服务器2 的 task/result/落盘路径落到 biz_file，并把已分发评论里的 ID 回填。

SET @db := DATABASE();

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'biz_file' AND COLUMN_NAME = 'server2_task_id'
);
SET @sql := IF(@exists = 0,
  'ALTER TABLE biz_file
     ADD COLUMN server2_task_id VARCHAR(128) NULL COMMENT ''服务器2任务ID'' AFTER server2_ref,
     ADD COLUMN server2_result_id VARCHAR(128) NULL COMMENT ''服务器2结果ID'' AFTER server2_task_id,
     ADD COLUMN server2_source_path VARCHAR(1024) NULL COMMENT ''服务器2落盘路径'' AFTER server2_result_id',
  'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE biz_file f
JOIN biz_circulation c ON c.file_id = f.file_id AND COALESCE(c.deleted, 0) = 0
SET
  f.server2_task_id = NULLIF(TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(c.comment_text, 'task=', -1), ' ', 1)), ''),
  f.server2_result_id = NULLIF(TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(c.comment_text, 'result=', -1), ' ', 1)), ''),
  f.server2_ref = COALESCE(
      NULLIF(f.server2_ref, ''),
      NULLIF(TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(c.comment_text, 'result=', -1), ' ', 1)), '')
  )
WHERE c.comment_text LIKE '%task=%'
  AND c.comment_text LIKE '%result=%'
  AND (f.server2_task_id IS NULL OR f.server2_task_id = '');

UPDATE biz_circulation
SET result_id = NULLIF(TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(comment_text, 'result=', -1), ' ', 1)), '')
WHERE comment_text LIKE '%result=%'
  AND (result_id IS NULL OR result_id = '')
  AND CHAR_LENGTH(TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(comment_text, 'result=', -1), ' ', 1))) BETWEEN 1 AND 64;
