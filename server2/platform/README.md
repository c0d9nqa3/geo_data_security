# Windows platform adapters

本目录只放Windows系统能力适配，不把系统命令散落到业务逻辑中。

计划模块：

- `veracrypt.py`：挂载/卸载项目专属加密卷。
- `sandbox.py`：受控进程、网络、文件系统隔离。
- `sysmon.py`：读取Windows事件日志中的Sysmon事件。
- `service.py`：Windows服务启动、停止和恢复。

开发阶段可以使用严格受限的本地适配器；只有在真实安装VeraCrypt、Sysmon并以目标账号运行后，才能标记系统能力验证通过。
