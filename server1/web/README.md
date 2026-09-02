# web：服务器1 终端 Web 界面（前后端分离 · 前端工程）

本目录是 **独立前端工程**（Vue 3 + Vite + TypeScript），部署在服务器1同机或由 Nginx/网关托管静态资源。

业务人员在内网终端用浏览器访问本界面，完成登录、项目、上传、任务与审计查询。

## 架构选择（已定）

采用 **前后端分离**：

| 部分 | 位置 | 职责 |
|---|---|---|
| 前端 | `server1/web/` | 页面与调用 REST API |
| 后端 API | `gateway/` `auth/` `project/` `ingest/` `task/` `circulation/` `audit/` | 登录权限、业务接口、服务间调用 |

同机部署 ≠ 前后端不分离。代码契约用 HTTP JSON API，后续：

- 前端调服务器1 `/api/*`
- 服务器1 内部调服务器2（服务身份认证）
- 前端按授权调服务器2只读结果接口

比 JSP/模板耦合更利于接 server2，也更符合成员1「Web 界面 + 后端 API」分工。

## 页面（成员1功能点）

- 登录 / 权限会话
- 工作台
- 项目管理
- 文件管理（上传入口）
- 任务管理
- 审计追溯

开发期 `src/api/client.ts` 使用 mock；`USE_MOCK = false` 后走真实 `/api`。

## 本地运行

```bash
cd server1/web
npm install
npm run dev
```

浏览器打开提示的地址（默认 `http://127.0.0.1:5173`）。  
开发代理：`/api` → `http://127.0.0.1:8081`（见 `vite.config.ts`）。

演示账号：用户名 `admin`（管理员）或任意名称（操作员），密码任意非空。

## 构建

```bash
npm run build
```

产物在 `dist/`，可由服务器1 静态托管或网关转发。
