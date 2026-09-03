# auth：登录认证与会话令牌

对应前端登录页 / 退出。

```text
前端登录 → 网关 /api/auth/login → auth 校验并签发 JWT
后续请求 → 网关 AuthFilter → auth 校验 Token → 业务模块
```

接口：

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`


无 Token 或 Token 无效：返回 401。

## Token 怎么缓存（当前方案，不用 Redis）

采用 **JWT + 本地内存会话表**：

1. **浏览器**：`localStorage` 保存 Token（前端已有）
2. **服务端**：`InMemoryTokenSessionStore`（ConcurrentHashMap）按 `tokenId` 缓存会话  
   - 登录写入  
   - 每次鉴权校验会话仍在  
   - 登出删除，Token 立即失效  

适合当前单机联调。服务重启后内存会话清空，需重新登录——可接受。

以后若多节点部署再考虑 Redis；现在架构核心不在这，不必上 Redis。

## 演示账号

- `admin` / `admin123`
- `operator` / `operator123`

当前 `sys_user.password` 存明文，方便本地看库联调。
