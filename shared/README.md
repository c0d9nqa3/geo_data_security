# shared：两台服务器共享的协议与模型

## 模块定位

本目录保存服务器1和服务器2必须一致的公共定义，防止两边各自定义导致任务、文件和审计记录无法关联。

## 计划内容

- `ids/`：项目ID、文件ID、任务ID、结果ID和审计事件ID规则。
- `models/`：项目、文件、任务、审核和结果的公共数据模型。
- `protocol/`：服务器1到服务器2的内部接口协议。
- `events/`：统一审计事件和链上存证事件格式。
- `config/`：配置模型、环境名和服务发现规则。
- `errors/`：公共错误码和错误响应格式。

## 必须统一的字段

`project_id`、`file_id`、`task_id`、`result_id`、`user_id`、`source_hash`、`result_hash`、`approval_status`、`watermark_id`、`audit_event_id`。

共享模型不能包含密码、私钥、原始文件内容或服务器本地绝对路径。
