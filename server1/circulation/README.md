# circulation：流转控制

新建项目、上传文件、提交任务时自动打开流转待办，不在本页单独发起申请。

- 待办状态 `pending`：仅管理员（`review` 权限）可见，列表可直接通过或拒绝。
- 审核通过后：右侧明细出现「提交分发授权」，把授权交给服务器2，不传输原始测绘文件。
- 操作员：可在项目/文件/任务页提交；看不到待办；审核完成后可看自己的单据。

对应前端「流转控制」：

- `GET /api/circulations?status=&page=&pageSize=` 分页查询（管理员看全部，操作员只看自己的非待办单据）
- `GET /api/circulations/{id}` 流转单明细
- `POST /api/circulations/{id}/approve` 审核通过（需 `review`）
- `POST /api/circulations/{id}/reject` 审核拒绝（需 `review`）
- `POST /api/circulations/{id}/distribute` 向服务器2提交分发授权

申请、审批、分发动作都通过 `audit` 模块写入业务审计事件。
