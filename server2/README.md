# server2：隔离计算与只读结果输出服务器

## 模块定位

服务器2是平台的数据安全处理核心。它保存项目加密数据，运行沙箱计算和四类水印，并向终端提供唯一的授权结果输出接口。

## 计划模块

- `ingress/`：只接收服务器1转交的任务和数据，不接受终端原始上传。
- `storage/`：VeraCrypt项目卷、项目目录和原始/结果文件生命周期管理。
- `sandbox/`：AppContainer Sandbox-Plus或等效受控任务执行。
- `compute/`：安全计算引擎、任务执行器、GDAL脱敏和精度处理。
- `watermark/`：GeoTIFF、SHP/GeoJSON、DLG、OSGB纹理水印模块。
- `metadata/`：PostgreSQL/PostGIS元数据和空间索引访问。
- `review/`：结果审核、授权状态和导出前检查。
- `readonly_output/`：只读结果下载、GeoServer在线服务和追溯查询。
- `audit/`：Sysmon、Elasticsearch和Kibana数据接入。
- `alert/`：ElastAlert2规则和异常行为告警。
- `blockchain/`：FISCO BCOS流转登记、归属登记和链上凭证查询。
- `forensics/`：水印证据、日志和链上记录的取证链条。

## 终端访问边界

服务器2对终端只开放审核通过结果的只读接口。结果接口必须按用户、项目、任务、结果ID和短时授权令牌校验，不提供目录列表、模糊路径、任意文件下载或上传功能。

服务器2不对终端开放数据库、Elasticsearch管理接口、FISCO BCOS管理接口、VeraCrypt盘符、Windows远程管理端口和沙箱管理接口。
