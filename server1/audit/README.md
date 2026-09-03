# audit：服务器1业务审计

记录服务器1上的登录、项目、上传、任务、审批和状态操作。

本目录负责业务事件产生和提交，不直接实现 Elasticsearch 底层管理，也不保存链上私钥。
事件字段对齐 `shared/events`：用户、项目、文件、任务、结果、操作、时间、源地址、源/结果哈希、处理状态。

对应前端「审计追溯」：

- 各业务模块调用 `AuditRecorder` 提交事件（写入 `biz_audit_event`）
- `GET /api/audit/events` 追溯查询（可选 `action`、`result`）
