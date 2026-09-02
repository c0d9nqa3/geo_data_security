# 配置目录

本目录只保存配置模板和配置说明，不保存真实环境的密码、证书、私钥、VeraCrypt 密钥文件或客户数据。

## 配置原则

- `test` 用于当前远程测试环境。
- `production` 用于甲方内网生产环境。
- 服务器地址、端口、证书路径和数据目录均通过配置注入。
- 终端数量不写死，生产默认按至少11台终端设计。
- 服务器1负责接收，服务器2负责只读结果输出。

## 计划配置文件

- `server1.test.example.yaml`：服务器1测试配置示例。
- `server2.test.example.yaml`：服务器2测试配置示例。
- `server1.production.example.yaml`：服务器1生产配置示例。
- `server2.production.example.yaml`：服务器2生产配置示例。
- `network-policy.example.yaml`：终端、服务器1、服务器2的访问策略模板。

真实配置文件应由部署人员在目标环境中生成，并放在不提交 Git 的本地目录。
