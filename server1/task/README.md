# task：任务管理

对应前端「任务管理」：对**已入库文件**发起受控处理作业（水印 / 脱敏），跟踪审批、转交服务器2、进度和结果索引。

- `GET /api/tasks` 分页列表（含处理阶段、流转状态、结果索引）
- `GET /api/tasks/{taskId}` 作业详情
- `POST /api/tasks` 发起处理（文件必须已分发入库）
- `POST /api/tasks/{taskId}/sync` 同步服务器2处理进度 / 回写结果索引
- `POST /api/tasks/{taskId}/download` 领取结果索引（哈希与存证摘要；结果文件在服务器2只读接口）

任务必须绑定 project_id、file_id、user_id 和 task_id。服务器1负责业务层任务控制，实际测绘处理由服务器2执行。
