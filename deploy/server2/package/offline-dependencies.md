# server2 离线依赖清单

## 当前本地已有（不进入代码包）

| 软件 | 本地文件 | 用途 | 本机验证 |
|---|---|---|---|
| VeraCrypt 1.26.29 x64 | `deploy/offline/packages/VeraCrypt_1.26.29_Machine_X64_wix_en-US.msi` | 加密卷 | 已创建/挂载/重挂载测试卷 |
| Sysmon 15.21 x64 | `deploy/offline/packages/Sysmon_15.21_X64_portable_en-US.zip` | 主机行为 | 未安装；需管理员 |

## 服务器2必须补齐

| 软件/文件 | 状态 | 说明 |
|---|---|---|
| Python 3.11 x64 | 待服务器安装 | 主环境与 TrustMark 环境 |
| uv | 待服务器安装 | 推荐的环境和锁文件安装器 |
| TrustMark Python 0.9.0 | 可从受控 PyPI/离线 wheel 安装 | 公开包只有代码，不含模型 |
| TrustMark Q 5个模型文件 | 已在开发机核验 | 单独离线介质，安装脚本校验 MD5 |
| Elasticsearch | 未安装 | 审计检索；当前代码只写 JSONL |
| Kibana | 未安装 | 审计展示 |
| ElastAlert2 | 未安装 | 异常告警 |
| PostGIS/PostgreSQL | 未安装 | 空间数据库计算路径 |
| FISCO BCOS 节点/证书 | 未部署 | 链上存证；证书私钥不能入包 |
| Windows AppContainer/等效沙箱 | 未完成部署 | 当前只有进程白名单+超时边界 |

## 不允许放进任何代码包

- 客户 SHP/GeoTIFF/OSGB/Mesh 数据
- VeraCrypt `.hc`/`.vc`/`.vhd` 卷
- 密码、服务令牌、工作区密钥
- TLS 证书和私钥
- FISCO BCOS 证书和私钥
- 真实 ES/PostGIS/FISCO 地址和凭据

## 当前安装顺序

1. Windows/Python/uv
2. 主环境依赖
3. TrustMark 独立环境依赖
4. TrustMark 模型和 MD5 核验
5. VeraCrypt 安装、创建并挂载生产卷
6. 配置 `server2.env`
7. 运行 `check_server2.ps1`
8. 启动 server2
9. 再按部署批次安装 Sysmon/ES/PostGIS/FISCO/告警组件
