# watermark：四类测绘数据水印

统一封装四类水印模块：GeoTIFF、SHP/GeoJSON、DLG、OSGB纹理。

原则：GeoTIFF和OSGB只允许像素层按方案发生微小变化；SHP/GeoJSON增加加密属性字段；DLG写入约定的元数据区；不修改坐标、拓扑或几何。

每个处理结果必须保存源文件哈希、结果哈希、watermark_id和处理参数，并接入审计。