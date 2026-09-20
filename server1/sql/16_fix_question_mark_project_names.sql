-- 早期用错误编码写入的项目名只剩下 '?'（HEX 3F），无法从库里还原原文。
-- 按当时联调用途补回可读名称；下拉框始终读 biz_project。
SET NAMES utf8mb4;

UPDATE biz_project
SET project_name = '上传审核分发联调'
WHERE project_id = 'prj_1789540493779' AND project_name LIKE '%?%';

UPDATE biz_project
SET project_name = '实拍9081联调'
WHERE project_id = 'prj_1789550668887' AND project_name LIKE '%?%';

UPDATE biz_project
SET project_name = '实拍9081联调-补传'
WHERE project_id = 'prj_1789609063045' AND project_name LIKE '%?%';

UPDATE biz_project
SET project_name = 'L14未命名TIF'
WHERE project_id = 'prj_1789610801094' AND project_name LIKE '%?%';
