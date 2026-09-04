# server2 部署包清单（本地已验证）

## 已生成并检查

- `package/README.md`
- `package/server2.env.example`
- `package/install_server2.ps1`
- `package/install_trustmark_models.ps1`
- `package/check_server2.ps1`
- `package/start_server2.ps1`
- `package/build_server2_package.ps1`
- `package/offline-dependencies.md`

## 包类型

当前生成的是**代码包**，不是包含所有第三方软件的离线安装盘。这样可以避免把大模型、客户数据、密码和证书错误地打进 Git 或 ZIP。

生成命令：

```powershell
powershell -ExecutionPolicy Bypass -File deploy\server2\package\build_server2_package.ps1 `
  -AppRoot C:\GeoDataSecurity\app `
  -OutputZip C:\GeoDataSecurity\GeoDataSecurity-server2-code.zip
```

## 服务器2上必须另行准备

- Python 3.11 x64
- uv，或经批准的 Python 包镜像/离线 wheelhouse
- TrustMark 5个模型文件（安装脚本会校验 MD5）
- VeraCrypt 安装包和生产卷（如启用加密存储）
- 生产令牌、工作区密钥、证书（通过本地安全存储注入）

## 可选基础设施

Sysmon、Elasticsearch、Kibana、ElastAlert2、PostGIS、FISCO BCOS 不由当前代码包自动安装。它们需要部署环境审批、版本确认、网络白名单和独立凭据。
