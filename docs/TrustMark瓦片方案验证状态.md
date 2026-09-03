# GeoTIFF 鲁棒水印：TrustMark 瓦片方案验证报告（2026-09-03）

## 结论先行

在真实 Landsat 影像（B1~B7，8111×7271、uint8、EPSG:32644）上，
**1024×1024 瓦片化 TrustMark-Q + BCH_SUPER 嵌入 + 三路解码**通过全部点名场景：

- **B1~B7 全波段 × 21 场景 = 147/147（100%）识别**
- 场景含：任意位置随机裁剪 25%/75%（各 3 批次）、中心裁剪 25%/50%/75%、缩放 25%/50%/75%/125%、
  JPEG q90、PNG 转换、噪声 σ=2（3 批次）、高斯滤波、中值滤波、重采样+重新投影（UTM→4326→原网格）
- **删自定义 GDS 标签补充实测：5/5 通过**（全图/裁剪25/裁剪75/缩放25/缩放75）
- 嵌入 PSNR 45.03~47.14dB（>40dB 达标），uint8 原格式保留，CRS/transform 完整
- 之前自写版 0/7 的缩放 25%、重投影两项，本方案均为 7/7

## 为什么换掉自写 DWT/DCT/SVD 鲁棒版

自写 `robust_geotiff_watermark.py`（cd1b0c92 已提交）在真实 uint8 影像上：
- 任意/中心裁剪 25%、75%：7/7 通过（512 瓦片重复 + 多数投票）
- 缩放 50%/75%/125%、JPEG、噪声、滤波、删标签：通过
- **缩放 25%：0/7 失败**（512 载体缩至 128×128，高频被重采样删除）
- **重采样+重新投影：0/7 失败**（UTM↔经纬度像元不可直比）

SIFT 特征同步实验版（feature_robust_watermark.py）：原图自检失败（0x1681F92A），未达门槛。

## 为什么是 TrustMark（成熟实现）

- Adobe 官方开源，模型已针对 JPEG/缩放/裁剪/噪声训练（noise_config 含 resized_crop、severity=high）
- 100bit payload + BCH 纠错；BCH_SUPER = 40bit = 最强纠错档
- CPU 可跑（本机 torch 2.1.2+cpu，单瓦片 encode ~0.3s）
- 只改像素值，不碰坐标/投影 → 满足"只增加标识信息"原则

**关键事实：TrustMark 单幅整图嵌入不抗"裁出小块直接解码"**（裁剪 25% 后普通 decode 全失败）。
原因是整图残差是单码字拉伸，裁剪破坏码字频率分布；官方 BBox detector 解决的是"合成图定位"，
不是深裁剪。**瓦片化**（每 1024×1024 独立嵌入同一 40bit 载荷）才让任意 25% 裁剪块内必含完整码字周期。

## 验证过的架构

### 嵌入（embed）
- 读 GeoTIFF：保留原 profile（dtype=uint8、CRS、transform、尺寸）
- 单波段灰度 → RGB 复制（TrustMark 需要 3 通道）
- 按 1024×1024 网格逐瓦片 `tm.encode(tile, payload32bit, MODE=binary, WM_STRENGTH=1.0)`
- 取 RGB 第 0 通道写回单波段 GeoTIFF
- 全幅 8111×7271：64 瓦片 / ~20s（CPU）
- 每波段 PSNR 45.03~47.14dB（>40dB 达标）
- 结果文件存 runtime/trustmark_full_tiled/B{N}_full_tiled.tif（不入库）

### 解码（extract）＝三路合并
1. **DETECTFIRST**：bbox detector 整图定位后解码（裁剪块含完整瓦片时一击命中）
2. **网格对齐窗口**：按 1024×scale 网格滑窗（缩放/JPEG/重投影回原网格后相位保持 0）
3. **细滑动窗口**：步长 win/8（裁剪改变网格相位时兜底）

B1 实际命中分布：裁剪 25%/75% 走 detect 或细滑窗；resize/JPEG/噪声/滤波/重投影全走网格窗口
（attempts 1~29，单场景 6~11s CPU）。

### 重投影（用户点名难点）
- 32644→4326 是强非线性扭曲，瓦片成不规则四边形 → 任何矩形网格都失配
- **解法：GDAL 逆投影回原 CRS 原网格**（dst_transform=原始 tf）再网格扫描 → 通过
- 前提：提取方知道原 CRS/transform（平台侧标签 GDS_* 或任务记录持有）

## 运行环境（独立 venv，勿并入主项目）

- `runtime/trustmark_venv/`：Python 3.11 + torch 2.1.2+cpu + torchvision 0.16.2 + numpy 1.26.4
  + lightning + omegaconf + einops + opencv-python-headless + rasterio + pyproj
- 主项目 .venv 是 numpy 2.x，与 torch 2.1.2 不兼容 → **TrustMark 必须走独立解释器**
  （子进程调用或单独服务）
- 模型文件（已下载、MD5 已核对）：
  - encoder_Q.ckpt `700328b8754db934b2f6cb5e5185d81f`
  - decoder_Q.ckpt `4ced90e9cfe13e3295ad082887fe9187`
  - trustmark_bbox_Q.ckpt `9d15428a33e15140ea16aa378416d304`
  - trustmark_Q.yaml / trustmark_bbox_Q.yaml
  - 位于 runtime/trustmark_source/python/trustmark/models/（已被 .gitignore 排除）

## 关键技术事实（防止重复踩坑）

1. TrustMark `encode(img, secret, MODE="binary")`，secret 是 **bit 字符串**（32bit 载荷
   = format(0xA5A5F00D,"032b")），不是 hex 文本。MODE="binary" 解码返回 bit 串，取前 32bit。
2. BCH_SUPER 编码后是 40bit 码字（32bit 业务标识 + 8bit 冗余），恢复取前 32bit。
3. `cv2.warpPerspective` 的四角单应性**不能**还原 UTM→4326 投影（曲线形变），
   必须用 GDAL reproject 回原网格。bbox 裁剪 + resize 可部分兜底（~50%），不够。
4. 瓦片化后**不能整幅图 decode**（多码字混叠解出错误码 0x41fb59a4 之类），必须窗口级解码。
5. 网格窗口必须相位对齐：缩放/JPEG 相位=0；裁剪相位=裁剪偏移 mod 1024（未知）→ 细滑动覆盖。

## 状态标记（诚实）

- ✅ 已实测：B1~B7 全波段 × 21 场景 = 147/147（100%），含裁剪 25%/75% 随机×3、缩放 25%~125%、
  JPEG/PNG、噪声×3、高斯/中值、重投影（4326→原网格）
- ✅ 已实测：删 GDS 自定义标签 5/5（解码不依赖自定义标签）
- ✅ 嵌入：B1~B7 每波段 64 瓦片 ~23s CPU；PSNR 45.03~47.14dB；uint8/CRS/transform 保留
- ⚠️ 重投影场景的解码前提：提取方能把嫌疑影像逆投影回原 CRS 网格（需原 CRS/transform，
  平台持有或从 GeoTIFF 标准地理参考推导；UTM→4326 不可直接矩形网格解码）
- ⏳ 未做：正式模块落地（TrustMark 引擎与 ProcessingService 的进程边界决策）、
  多影像多时相扩展、验收报告四类数据完整统计
- ⚠️ 算法路线：TrustMark 是 CNN 黑盒，偏离技术方案钦定 DWT+DCT+SVD —— 需决策，见"决策点"
