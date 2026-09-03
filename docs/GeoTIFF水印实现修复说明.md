# GeoTIFF水印实现修复说明

## 本次改造

针对真实Landsat B1～B7影像为`uint8`的问题，GeoTIFF水印输出恢复为原始`uint8`类型，不再依赖`float32`输出保存小数级变化。

处理逻辑：

```text
uint8 GeoTIFF
→ DWT
→ DCT
→ SVD分块量化
→ 增大整数域可保留的量化步长
→ 写回uint8
```

提取时从输出GeoTIFF的`GDS_WM_STEP`标签读取实际步长，避免嵌入和提取参数不一致。

## 真实影像验证

样本：B1～B7，8111×7271，EPSG:32644，uint8。

结果：

- 7/7波段水印提取正确；
- 7/7波段PSNR>40dB；
- 最低PSNR：48.64dB；
- 最高PSNR：50.35dB；
- 单波段最大耗时：9.116秒；
- CRS、Transform、范围、尺寸、波段数和`AREA_OR_POINT`保持；
- 输入输出数据类型均为`uint8`。

## 重要限制

本次结果只证明当前7个真实波段的基础嵌入测试通过，不代表最终鲁棒性指标已经完成。

尚未通过或尚未执行：

- 格式转换后识别率≥90%的批量测试；
- 裁剪后识别率测试；
- 缩放后识别率测试；
- 重采样和重新投影后识别率测试；
- 多批次样本嵌入成功率≥95%的统计。

另一个已实测事实：旧的`float32→uint8`转换会导致原水印丢失。因此正式鲁棒性测试必须从当前`uint8`输出版本重新开始，不能引用旧的float32结果。

## 测试命令

```bash
PYTHONPATH=server2/pipeline uv run python tests/run_real_geotiff_batch.py
uv run pytest -q
uv run python -m compileall -q server2 tests
git diff --check
```
