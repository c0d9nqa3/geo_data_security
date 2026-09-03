# deploy/server2 部署说明

## 环境要求（本机联调已验证，2026-09-04）

- Windows 10/11，Python 3.11（主 venv 由仓库 uv.lock 建立，numpy>=2）
- 可选：`runtime/trustmark_venv`（torch 2.1.2+cpu + trustmark 0.9.0 + 模型），
  提供 TrustMark-Q 鲁棒水印引擎（GeoTIFF 瓦片 + 纹理单码字）。缺省时自动回退
  基础 DWT/DCT/SVD 水印，鲁棒性不达标——**部署机必须装**
- 可选：VeraCrypt（真实卷存储闭环，见下）
- Sysmon/Elasticsearch/Kibana/PostGIS/FISCO BCOS/ElastAlert2：部署环境组件，
  本仓库只提供配置模板和离线包（sysmon/veracrypt），不随代码分发

## server2 服务启动

```bat
:: 主处理+审核+只读接口（内部端口 9081）
set GDS_WORKSPACE=V:\geo_data_security
set GDS_AUDIT_DIR=V:\geo_data_security\audit
set GEO_SECURITY_SERVER1_TOKEN=<secret injected at deploy>
set GDS_TRUSTMARK_PYTHON=<install>\trustmark_venv\Scripts\python.exe
cd server2\pipeline
..\..\.venv\Scripts\uvicorn geo_security.serve:app --host 0.0.0.0 --port 9081
```

角色装配（serve.py）：10 路由含 /health、/internal/tasks、/readonly/results/*；
workspace/审计目录/TrustMark 引擎全部由环境变量注入，代码无硬编码路径。

## VeraCrypt 真实卷闭环（本机已验证）

卷创建需管理员（UAC）。测试卷：`C:\Users\Steven\geo_vc_test\test_vc_volume.hc`
（200MB AES/SHA-512/NTFS）。密码走本地 secret 文件或环境变量，**不入库**。

```powershell
# 创建（弹 UAC，密码参数按部署机密策略注入）
Start-Process 'C:\Program Files\VeraCrypt\VeraCrypt Format.exe' -ArgumentList @(
  '/create','C:\path\volume.hc','/size','20G','/encryption','AES',
  '/hash','SHA-512','/filesystem','NTFS','/password',$secret,'/silent') -Verb RunAs -Wait
# 挂载（普通用户）
'C:\Program Files\VeraCrypt\VeraCrypt.exe' /volume C:\path\volume.hc /letter V /password $secret /quit /silent
```

`VeraCryptAdapter`（server2/platform/veracrypt.py）封装
create/mount/dismount/is_mounted；测试 tests/veracrypt_volume_test.py 验证
挂载、重挂载持久化、ProcessingService 结果落加密卷（卷缺失自动 skip）。

## 审计日志

`server2/audit/audit_log.py` 按天 JSONL（本地时区 ISO-8601）。API 动作：
TASK_SUBMITTED/COMPLETED/REJECTED/FAILED、RESULT_APPROVED、RESULT_MANIFEST_READ、
RESULT_FILE_DOWNLOADED、AUTH_DENIED。部署机由 filebeat/Logstash 摄入
Elasticsearch 保留≥180天（索引生命周期策略属部署配置）。

## 部署后验证

1. `GET /health` 返回 ok
2. server1 携 X-Service-Token 提交 SHP/GeoTIFF/TEXTURES 任务 → COMPLETED
3. 审核 → 终端 /readonly 下载，确认结果在 V: 卷内、审计目录有新行
4. 无 token 访问 /internal/* 返回 401 且审计 AUTH_DENIED
