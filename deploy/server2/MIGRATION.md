# server2 迁移与快速部署方案

## 一、迁移边界

迁移分为四个独立包，不把所有文件放在一个目录：

```text
GeoDataSecurity-Migration/
├── 01_code/              # Git代码包，约数百KB
├── 02_offline_bundle/    # Python依赖、TrustMark源码包、模型，约621MB
├── 03_customer_data/     # 客户SHP/GeoTIFF/OSGB/Mesh，单独传输，不入代码包
└── 04_secrets/           # 空目录；服务器现场生成密码、令牌、证书
```

当前开发机实际可迁移：

- `runtime/GeoDataSecurity-server2-code.zip`：代码包
- `runtime/server2_offline_bundle/`：完整离线包，约621MB
- `deploy/offline/packages/`：已有 VeraCrypt/Sysmon 安装包，可另行带走

当前不迁移：

- 开发机 `.venv/`
- `runtime/trustmark_venv/`
- `runtime/trustmark_source/`（代码包不依赖它）
- 开发机全部实验产物
- 开发机测试数据
- 测试用 VeraCrypt `.hc` 卷
- 任何密码、令牌、证书、私钥

## 二、服务器2目标目录

推荐服务器2使用以下固定布局：

```text
C:\GeoDataSecurity\
├── app\                         # 代码，只读发布目录
│   ├── server1/                 # 只保留仓库代码，不在server2启动
│   ├── server2/
│   ├── shared/
│   ├── config/
│   ├── deploy/
│   └── server2.env              # 现场生成，不进Git
├── runtime\
│   └── trustmark_venv\          # 独立TrustMark Python环境
├── offline\                     # 离线包临时目录，可安装后归档
└── logs\                        # 启动日志和系统安装日志
```

生产数据盘（推荐VeraCrypt挂载）：

```text
V:\geo_data_security\
├── incoming\                    # 仅服务器1内部接口写入
├── projects\                    # 原始数据、处理临时区、结果
├── results\                     # 审核通过前后的结果文件
├── audit\                       # JSONL审计；后续可由Filebeat/Logstash采集
└── state\
    └── server2.sqlite3          # 任务、结果元数据和审核状态
```

服务器2应用账号只需要对 `V:\geo_data_security` 有读写权限，对 `C:\GeoDataSecurity\app` 只读即可。安装账号和服务账号分离。

## 三、服务器职责边界

### 服务器1：控制面

负责：

- 用户认证和权限校验
- 接收终端上传
- 创建和编排任务
- 调用服务器2内部任务接口
- 查询任务状态
- 触发结果审核

不负责：

- 直接读取服务器2的VeraCrypt盘
- 直接访问服务器2 SQLite、审计目录、Elasticsearch、FISCO
- 向终端提供服务器2文件系统路径

### 服务器2：数据面

负责：

- 受控接收服务器1转交的任务
- 数据处理、水印、精度处理
- VeraCrypt加密卷中的项目数据
- SQLite任务状态和审核状态
- 审计日志
- 审核通过后的只读结果输出

不负责：

- 接收终端原始上传
- 向终端开放任意目录或数据库
- 向终端开放VeraCrypt盘符
- 允许用户输入任意路径或命令

### 终端

允许：

- 通过服务器1提交业务请求
- 通过服务器2只读接口读取已审核结果

禁止：

- 直接上传到服务器2
- 访问服务器2内部接口
- 访问服务器2数据库、审计系统、VeraCrypt和管理接口

## 四、最快迁移方式

### 推荐：移动硬盘/受控U盘

迁移内容只有：

1. `GeoDataSecurity-server2-code.zip`
2. `server2_offline_bundle` 整个目录
3. VeraCrypt/Sysmon安装包（如部署审批允许）
4. 客户数据单独目录（拿到后再传）

不要压缩后再拆分依赖包；621MB已是可直接复制的离线目录。

### 内网SMB

在源机和服务器2都能访问共享目录时，使用Windows `robocopy`：

```bat
robocopy "源机\runtime\server2_offline_bundle" "\\SERVER2\D$\GeoDataSecurity\offline" /E /Z /J /R:3 /W:5 /ETA /LOG:migration-bundle.log
robocopy "源机\runtime\GeoDataSecurity-server2-code.zip" "\\SERVER2\D$\GeoDataSecurity\" /Z /J /R:3 /W:5 /ETA
```

`/Z`支持断点续传，`/J`适合大文件。不要使用普通拖拽复制大包。

## 五、传输后校验

服务器2上执行：

```powershell
Get-FileHash D:\GeoDataSecurity\offline\SHA256SUMS.txt -Algorithm SHA256
```

对目录内文件逐个校验：

```powershell
Get-Content D:\GeoDataSecurity\offline\SHA256SUMS.txt | ForEach-Object {
  $p = $_ -split '  ', 2
  if (-not (Test-Path (Join-Path D:\GeoDataSecurity\offline $p[1]))) { throw "Missing: $($p[1])" }
  $actual = (Get-FileHash (Join-Path D:\GeoDataSecurity\offline $p[1]) -Algorithm SHA256).Hash.ToLower()
  if ($actual -ne $p[0]) { throw "Hash mismatch: $($p[1])" }
}
Write-Output 'SHA256 verification passed'
```

## 六、服务器2现场安装顺序

1. 管理员安装 `bootstrap\python-3.11.9-amd64.exe`
2. 安装uv：

```powershell
python -m pip install D:\GeoDataSecurity\offline\bootstrap\uv-0.9.9-py3-none-win_amd64.whl
```

3. 解压代码包到 `C:\GeoDataSecurity\app`
4. 离线安装：

```powershell
powershell -ExecutionPolicy Bypass -File D:\GeoDataSecurity\offline\package\install_server2_offline.ps1 `
  -AppRoot C:\GeoDataSecurity\app `
  -InstallRoot C:\GeoDataSecurity\runtime `
  -BundleRoot D:\GeoDataSecurity\offline
```

5. 安装脚本完成后，把 `D:\GeoDataSecurity\offline\models` 的模型按脚本逻辑安装到TrustMark环境
6. 安装并挂载VeraCrypt生产卷
7. 创建 `C:\GeoDataSecurity\app\server2.env`
8. 执行 `check_server2.ps1 -RequireTrustMark`
9. 启动 server2
10. 用 `/health`、测试任务、审核和只读下载做现场验收

## 七、第一阶段现场验收

先不要接入ES、FISCO和双网，先完成最小闭环：

```text
VeraCrypt挂载
→ server2启动
→ SQLite创建
→ 服务器1内部任务调用
→ 处理结果写入V盘
→ 审核状态写入SQLite
→ server2重启
→ 任务和审核状态仍存在
→ 只读结果仍可下载
```

这个闭环通过后，再安装和联调：

- Sysmon
- Elasticsearch/Kibana
- ElastAlert2
- PostGIS
- FISCO BCOS
- Windows服务注册
- 双网访问控制

## 八、当前不能在迁移包中宣称完成

- 100并发审计
- 180天日志保留
- 10秒告警
- 1GB SHP/10GB Mesh性能
- 真实OSGB/Mesh验证
- FISCO链上存证
- 真正AppContainer/等效沙箱
- 双网部署

这些必须在服务器2和目标网络实际安装、配置、测试后记录结果。
