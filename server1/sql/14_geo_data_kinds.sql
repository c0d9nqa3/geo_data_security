-- 七类测绘数据 data_kind 与客户确认名称对齐
-- 数字线划地图(DLG) / 数字正射影像(DOM) / 数字高程模型(DEM) / 数字栅格地图(DRG)
-- 基础地理实体数据(GEO_ENTITY) / 倾斜摄影Mesh三维模型(MESH) / 激光点云数据(POINT_CLOUD)

UPDATE biz_file SET data_kind = 'DLG'
WHERE data_kind IN ('DLG', '数字线划图', '数字线划地图');

UPDATE biz_file SET data_kind = 'DOM'
WHERE data_kind IN ('DOM', 'GeoTIFF', 'GEOTIFF', '遥感影像', '数字正射影像');

UPDATE biz_file SET data_kind = 'DEM'
WHERE data_kind IN ('DEM', '数字高程模型');

UPDATE biz_file SET data_kind = 'DRG'
WHERE data_kind IN ('DRG', '数字栅格地图');

UPDATE biz_file SET data_kind = 'GEO_ENTITY'
WHERE data_kind IN ('GEO_ENTITY', 'SHP_GEOJSON', 'SHP/GeoJSON', '矢量专题', '基础地理实体数据');

UPDATE biz_file SET data_kind = 'MESH'
WHERE data_kind IN ('MESH', 'OSGB', '倾斜摄影三维', '倾斜摄影Mesh三维模型');

UPDATE biz_file SET data_kind = 'POINT_CLOUD'
WHERE data_kind IN ('POINT_CLOUD', '点云', '激光点云', '激光点云数据');
