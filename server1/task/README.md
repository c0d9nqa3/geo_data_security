# task：任务管理

对应前端「任务管理」：列表筛选、提交处理任务。

- `GET /api/tasks`
- `POST /api/tasks`

任务必须绑定 project_id、file_id、user_id 和 task_id。服务器1负责业务层任务控制，实际测绘处理由服务器2执行。
