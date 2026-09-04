# Server2 本地部署包

这个目录包含服务器2的代码部署脚本，不包含客户数据、密钥、VeraCrypt卷或TrustMark模型。

## 推荐部署顺序

1. 在服务器2安装 Python 3.11 x64 和 `uv`。
2. 解压代码包到 `C:\GeoDataSecurity\app`。
3. 运行 `install_server2.ps1`，建立主环境和独立 TrustMark 环境。
4. 准备独立的 `trustmark_models` 目录，运行 `install_trustmark_models.ps1`。
5. 复制 `server2.env.example` 为 `C:\GeoDataSecurity\app\server2.env`，填写本地路径和密钥。
6. 运行 `check_server2.ps1`。
7. 运行 `start_server2.ps1`。

## 代码包与模型包分离

### 代码包

由 `build_server2_package.ps1` 生成，包含：

- `server2/` Python代码
- `shared/`
- `config/`模板
- `deploy/server2/package/`安装、检查、启动脚本
- 文档和测试

### 模型包

单独通过受控介质提供，目录必须包含：

```text
encoder_Q.ckpt
 decoder_Q.ckpt
trustmark_Q.yaml
trustmark_bbox_Q.ckpt
trustmark_bbox_Q.yaml
```

模型 MD5：

```text
encoder_Q.ckpt       700328b8754db934b2f6cb5e5185d81f
 decoder_Q.ckpt      4ced90e9cfe13e3295ad082887fe9187
trustmark_Q.yaml     fe40df84a7feeebfceb7a7678d7e6ec6
trustmark_bbox_Q.ckpt 9d15428a33e15140ea16aa378416d304
trustmark_bbox_Q.yaml 749b0d62106f8f6648e6f781c3143105
```

`install_trustmark_models.ps1` 会先校验 MD5，再复制到独立 TrustMark 环境的 `trustmark/models/`。

## 持久化

SQLite数据库由 `GDS_TASK_DATABASE` 指定，默认建议放在 VeraCrypt 已挂载盘内：

```text
V:\geo_data_security\state\server2.sqlite3
```

数据库保存任务、结果元数据、用户归属和审核状态；大文件保存在 `GDS_WORKSPACE` 的项目目录。
服务重启后任务状态和审核状态从 SQLite 恢复，不依赖进程内存。

## 当前不属于本地代码包即可完成的事项

- Sysmon安装与管理员授权
- Elasticsearch/Kibana/ElastAlert2部署
- PostGIS部署
- FISCO BCOS节点、证书和链上交易
- 双网防火墙和服务器1联调
- 1GB SHP、10GB Mesh、100并发、180天、10秒等验收实测
