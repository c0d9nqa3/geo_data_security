# TrustMark 引擎接入 server2：实现与验证记录（2026-09-04）

## 目标

将已验证的 TrustMark 瓦片水印方案从"实验脚本"提升为 server2 正式 GeoTIFF 处理引擎，
并接入 ProcessingService 与 /internal/tasks，使 server1 任务能真正调用。

## 新增正式模块

```
server2/pipeline/geo_security/
  trustmark_geotiff_runner.py   # 独立 venv 运行器（embed/extract）
  trustmark_engine.py           # 主环境侧子进程桥
```

### 为什么子进程桥

主项目 .venv 使用 numpy>=2，torch 2.1.2（numpy<2 时代构建）无法共存 →
TrustMark 必须跑在独立环境 `runtime/trustmark_venv`（torch 2.1.2+cpu、numpy 1.26、
trustmark 0.9.0 editable、rasterio、pyproj、opencv）。主环境通过 subprocess 调用，
不 import torch。部署时用环境变量配置：

```
GDS_TRUSTMARK_PYTHON   # 独立 venv python 路径
GDS_TRUSTMARK_RUNNER   # runner 脚本路径
```

### runner embed

- 读 GeoTIFF：要求 uint8 单波段（TrustMark 灰度→RGB 复制，取 R 通道写回）
- 1024×1024 瓦片网格，每瓦片独立嵌入同一 32bit 载荷（BCH_SUPER 40bit 码字）
- 保留原 profile：dtype/CRS/transform/tags
- **记录原空间参考标签**：GDS_TM_SRC_CRS / GDS_TM_SRC_TF / GDS_TM_SRC_W / GDS_TM_SRC_H
  （重投影攻击时用于逆投影回原网格）
- 输出 JSON：{tiles, psnr_db, dtype, width, height}

### runner extract（重投影感知）

1. 读 GDS_TM_SRC_* 标签；若影像当前 CRS ≠ 记录原 CRS → GDAL reproject
   回**记录的原网格**（dst_transform=原 tf、尺寸=原 W/H），瓦片网格完美对齐
2. bbox_detect 整图定位（裁剪/合成场景）
3. 多尺度窗口扫描兜底：尺度序 [1.0,0.75,0.625,0.5,0.375,0.25,0.1875,0.125,1.25,1.5,2.0]，
   每尺度 45 次预算（grid 对齐 + step=win//8 细滑，中心优先），总预算 400
4. 输出 JSON：{detected, method, attempts, window, warped}

### 关键调试结论（踩坑记录）

1. TrustMark decode 输入需 RGB 3 通道；单波段需 np.repeat 复制。
2. BCH_SUPER 编码 40bit（32bit 业务 + 8bit 冗余），提取取前 32bit。
3. 瓦片化后**不能整幅 decode**（多码字混叠 → 错误码），必须窗口级解码。
4. **bbox detector 对 1px 裁剪偏移极敏感**：同图 (1014,909) 命中、(1013,908) 失败。
   不可单独依赖 → 窗口扫描兜底必须存在。
5. 裁剪改变瓦片网格相位：窗口步长须 ≤ win/8（128px）才能容差内命中任意相位；
   步长 256/512 会整体漏过。
6. 重投影（UTM→4326）后瓦片成不规则四边形：不能直接矩形网格扫，必须 GDAL
   逆投影回原 CRS+原网格。4 角点单应性 warp 不足以还原（曲线形变）。
7. 删标签场景：PNG 无标签仍可靠（窗口扫描不依赖标签）；删标签+重投影组合
   无原网格信息，需 SIFT 特征定位（未完成，见限制）。
8. extract 每场景为独立子进程（模型加载 ~15s + 解码），单场景 17-40s CPU。

## ProcessingService 接入

- 构造注入：`ProcessingService(workspace, key, trustmark_engine=engine)`
- 未配置引擎时 GeoTIFF 回退基础 DWT/DCT/SVD（保持既有测试语义）
- 统一 artifact：GeoJSON(属性水印) / GeoTIFF(像素水印) / OSGB_TEXTURES(纹理水印)
- 失败自动清理结果目录；API 层任务标记 FAILED 并记录 error
- /internal/tasks 支持 data_type: GeoJSON/SHP, GeoTIFF/GTIFF, TEXTURES/OSGB_TEXTURES/OSGB
- 只读下载修复：目录型 artifact（纹理集）正确解析结果目录

## 验证结果

### 单元/集成测试（tests/，全量 23 passed）

- task_e2e_dispatch_test.py：三种数据类型经 /internal/tasks 提交→查询→审核→下载；
  失败任务 FAILED 且结果目录被清理（注入假引擎）
- trustmark_integration_test.py：真实 venv 引擎——合成 uint8 GeoTIFF embed→extract
  检出 0x1234ABCD；ProcessingService 路由；API 任务端到端下载（真实引擎，3 passed）
- trustmark_reproject_test.py：1024 合成 32644 → embed → reproject 4326 → extract
  检出 0x1357BDFF（warped=true，1 passed）
- 注：venv 缺失时以上测试 skip（部署机器需先建 runtime/trustmark_venv）

### 真实 B1~B7 引擎链矩阵（tests/run_engine_matrix_b1b7.py）

引擎（子进程 runner）embed 真实 Landsat 波段，生成攻击场景文件，逐场景 engine.extract：
19 场景 + 重投影(4326, 保标签) + 删标签全图 = 21 场景/波段。

- B1：21/21 全过（reproject warped=true 检出；notags 窗口 2 次命中）
- B2~B7：各 21/21 全过（每波段约 7min CPU）
- **合计 B1~B7×21 场景 = 147/147 = 100%**
- 场景：随机裁剪 25%/75%×3、中心裁剪 25/50/75%、缩放 25~125%、
  JPEG q90、噪声×3、高斯、中值、重投影 4326、删 GDS 标签全图
- 耗时：典型成功场景 15-40s（bbox_detect 命中 ~16s；深缩放 window 扫描
  267 次 ~40s）；重投影 warped=true 每波段 2 次尝试命中

### 引擎链 vs 实验脚本矩阵（等价性说明）

- 实验脚本（9fafdd3 验证 147/147）：同进程内直接调 TrustMark，攻击图在内存中。
- 引擎链（本轮 da44f5b 后）：攻击图**落盘为文件**，extract 走正式子进程 runner
  （每次启动加载模型 ~8s），并新增两路能力：重投影自动逆投影（warped=true）
  与删标签全图（notags_full）——实验结果全部继承且更强。

## 限制（诚实）

- 删标签 + 重投影组合：无原网格信息，runner 无法自动逆投影 → 需要特征定位
  （SIFT/ORB + 几何估计），未实现。影响面：外部工具同时删标签并改 CRS 的极端场景。
- extract 单场景 17-40s（CPU 子进程），批处理吞吐需并行化或 GPU 才适合大规模审计。
- 主 venv 全量测试在无 trustmark venv 的机器：23 → 20 passed + 3 skipped。
