# 服务器1 MySQL 表与前端接口对照说明

依据：`docs/架构冻结说明.md`、`docs/接口边界说明.md`、`server1` 模块职责，以及当前前端页面按钮。

原则：

- MySQL 只存 **业务元数据/索引/状态**，不存原始测绘文件内容；
- Token 会话当前用 **内存缓存**（不依赖 Redis）；
- 大文件与水印执行在服务器2，服务器1只编排并写索引。

## 1. 本地执行顺序

在 MySQL 客户端依次执行：

```text
server1/sql/01_create_database.sql
server1/sql/02_schema_server1.sql
server1/sql/03_seed_test_data.sql
```

已有库若缺流转单新字段，再执行 `04_alter_circulation.sql`；若缺 `apply_type`，再执行 `05_alter_apply_type.sql`；若字段注释为空，再执行 `06_comment_circulation.sql`；若缺逻辑删除字段，再执行 `07_alter_deleted.sql`；若要把登录密码改成明文列，再执行 `08_plain_password.sql`。

演示账号：

| 用户名 | 密码 | 角色 |
|---|---|---|
| admin | admin123 | 管理员 |
| operator | operator123 | 操作员 |

后端（`app`）默认连接：`127.0.0.1:3306` / 库 `geo_server1` / 用户 `root` / 密码 `123456`（可用环境变量 `SERVER1_DB_*` 覆盖）。

## 2. 表清单（共 12 张）

| 表名 | 用途 |
|---|---|
| `sys_user` | 登录用户（`password` 当前为明文，仅本地演示） |
| `sys_role` | 角色 |
| `sys_permission` | 权限点 |
| `sys_user_role` | 用户-角色 |
| `sys_role_permission` | 角色-权限 |
| `biz_project` | 项目 |
| `biz_project_member` | 项目成员 |
| `biz_file` | 上传文件索引 |
| `biz_task` | 处理任务 |
| `biz_circulation` | 流转审核单 |
| `biz_result_index` | 结果索引（服务器2回传） |
| `biz_audit_event` | 业务审计事件 |

## 3. 前端页面 → 接口 → 表

### 3.1 登录页

| 前端操作 | 接口 | 读写表 | 逻辑要点 |
|---|---|---|---|
| 进入平台 | `POST /api/auth/login` | 读 `sys_user`/`sys_user_role`/`sys_role_permission`；写 `biz_audit_event` | 校验密码哈希，签发 JWT，内存登记会话 |
| （布局内退出） | `POST /api/auth/logout` | 写 `biz_audit_event` | 删内存会话 |
| 当前用户 | `GET /api/auth/me` | 读用户/角色缓存信息 | 必须带 Bearer Token |

### 3.2 工作台

| 前端展示/按钮 | 接口 | 表 |
|---|---|---|
| 在管项目 | `GET /api/projects` 计数 | `biz_project` |
| 测绘文件 | `GET /api/files` 计数 | `biz_file` |
| 运行中任务 | `GET /api/tasks` 过滤 queued/running | `biz_task` |
| 待处理告警 | `GET /api/audit/events` 过滤 denied/error | `biz_audit_event` |
| 最近任务 / 查看全部 | `GET /api/tasks` | `biz_task`（关联项目名可读 `biz_project`） |
| 最新审计 / 进入审计页 | `GET /api/audit/events` | `biz_audit_event` |
| 导入测绘数据 | 跳转文件页 → 上传接口 | 见文件管理 |

### 3.3 项目管理（`project` 模块）

| 前端操作 | 接口 | 表 | 逻辑 |
|---|---|---|---|
| 列表/搜索 | `GET /api/projects` | `biz_project` + `biz_project_member` + 文件数统计 `biz_file` | 按成员可见范围过滤 |
| 新建项目 → 创建 | `POST /api/projects` | 写 `biz_project`、`biz_project_member`、`biz_circulation`、`biz_audit_event` | 生成 `project_id`，自动打开流转待办 |

### 3.4 文件管理（`ingest` 模块）

| 前端操作 | 接口 | 表 | 逻辑 |
|---|---|---|---|
| 列表/按项目筛选 | `GET /api/files?projectId=` | `biz_file` + `biz_project` | 校验项目成员权限 |
| 上传数据 | `POST /api/files/upload` | 写 `biz_file`、`biz_circulation`、`biz_audit_event` | 写入文件索引并自动打开流转待办；通过并分发后才转交服务器2 |

### 3.5 任务管理（`task` 模块）

| 前端操作 | 接口 | 表 | 逻辑 |
|---|---|---|---|
| 列表/状态筛选 | `GET /api/tasks?projectId=&status=` | `biz_task` + `biz_project` + `biz_file` | Token 鉴权 + 项目权限 |
| 提交任务 | `POST /api/tasks` | 写 `biz_task`、`biz_circulation`、`biz_audit_event` | 写入任务并自动打开流转待办；通过并分发后才交给服务器2执行 |

### 3.6 审计追溯（`audit` 模块）

| 前端操作 | 接口 | 表 |
|---|---|---|
| 动作/结果筛选列表 | `GET /api/audit/events?action=&result=` | `biz_audit_event` |

### 3.7 流转控制（`circulation` 模块）

新建项目、上传文件、提交任务会**自动**进入流转待办，不在本页单独发起申请。待办仅管理员（`review`）可见；通过后可提交分发授权到服务器2（不传原始文件）。

| 能力 | 接口 | 表 |
|---|---|---|
| 查询待办/单据 | `GET /api/circulations?status=&page=&pageSize=` | `biz_circulation` 分页（无 review 看不到 pending） |
| 明细 | `GET /api/circulations/{id}` | `biz_circulation` + 项目/文件 |
| 审批 | `POST .../approve` `.../reject` | 更新流转单状态与审批意见 |
| 分发授权 | `POST .../distribute` | `distribute_status=dispatched`，并回写项目/文件/任务状态 |
| 逻辑删除 | `POST .../delete` | `deleted=1`，列表不再返回 |

## 4. 建议接口清单（服务器1 `app` 进程对外，经 gateway 过滤器）

```text
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me

GET    /api/projects
POST   /api/projects

GET    /api/files
POST   /api/files/upload

GET    /api/tasks
POST   /api/tasks
GET    /api/tasks/{taskId}

GET    /api/audit/events

GET    /api/circulations
GET    /api/circulations/{id}
POST   /api/circulations/{id}/approve
POST   /api/circulations/{id}/reject
POST   /api/circulations/{id}/distribute
POST   /api/circulations/{id}/delete

GET    /api/health
GET    /api/ready
```

除登录与健康检查外，全部要求：`Authorization: Bearer <token>`。

## 5. 与服务器2 的边界（不建在本库的内容）

以下不进 `geo_server1` MySQL：

- VeraCrypt 卷内原始/结果文件；
- PostGIS 空间库（属服务器2）；
- Elasticsearch 主机/处理日志详档（服务器2采集，服务器1可查业务审计表）；
- FISCO BCOS 节点私钥与完整链数据（只在 `biz_result_index.chain_proof` 存摘要）。
