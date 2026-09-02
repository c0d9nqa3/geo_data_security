# server2 服务程序

服务器2程序的源码目录。服务器2负责数据面的安全处理和结果输出，终端只访问其中的严格只读结果接口。

目录职责：

- `ingress/`：接收server1转交的数据和任务。
- `storage/`：VeraCrypt项目卷和文件生命周期。
- `sandbox/`：受控计算和项目空间隔离。
- `compute/`：安全计算、GDAL和处理引擎。
- `watermark/`：四类测绘数据水印。
- `metadata/`：PostGIS元数据和空间索引。
- `review/`：结果审核和输出前检查。
- `readonly_output/`：终端只读结果接口。
- `audit/`：处理、文件和主机审计接入。
- `alert/`：异常告警。
- `blockchain/`：FISCO BCOS存证适配。
- `geoserver/`：授权地图/模型服务。
- `sysmon/`：Windows主机行为采集配置。
- `forensics/`：溯源和取证报告。

不在本目录提供终端上传接口，不提供任意文件路径读取，不向终端开放管理端口。