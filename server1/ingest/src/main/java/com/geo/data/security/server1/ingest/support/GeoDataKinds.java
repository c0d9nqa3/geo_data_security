package com.geo.data.security.server1.ingest.support;

import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 工作台体量分析用的七类测绘数据。页面上传、统计曲线与库内 data_kind 都以这里为准。
 */
public final class GeoDataKinds {

    public record Def(String dbCode, String uiLabel, String title, String color) {
    }

    public static final List<Def> ALL = List.of(
            new Def("DLG", "DLG", "数字线划地图", "#22d3ee"),
            new Def("DOM", "DOM", "数字正射影像", "#3b82f6"),
            new Def("DEM", "DEM", "数字高程模型", "#10b981"),
            new Def("DRG", "DRG", "数字栅格地图", "#a855f7"),
            new Def("GEO_ENTITY", "基础地理实体数据", "基础地理实体数据", "#f59e0b"),
            new Def("MESH", "倾斜摄影Mesh三维模型", "倾斜摄影Mesh三维模型", "#fb923c"),
            new Def("POINT_CLOUD", "激光点云数据", "激光点云数据", "#818cf8")
    );

    private static final Map<String, Def> BY_DB = ALL.stream()
            .collect(Collectors.toUnmodifiableMap(d -> d.dbCode().toUpperCase(Locale.ROOT), Function.identity()));

    private GeoDataKinds() {
    }

    public static Def byDbCode(String dbCode) {
        if (dbCode == null || dbCode.isBlank()) {
            return null;
        }
        return BY_DB.get(normalizeDbCode(dbCode).toUpperCase(Locale.ROOT));
    }

    public static String normalizeDbCode(String dbKind) {
        if (dbKind == null || dbKind.isBlank()) {
            return "OTHER";
        }
        String key = dbKind.trim();
        String upper = key.toUpperCase(Locale.ROOT);
        return switch (upper) {
            case "DLG", "数字线划图", "数字线划地图" -> "DLG";
            case "DOM", "数字正射影像" -> "DOM";
            case "DEM", "数字高程模型" -> "DEM";
            case "DRG", "数字栅格地图" -> "DRG";
            case "GEOTIFF", "遥感影像" -> "DOM";
            case "SHP_GEOJSON", "SHP/GEOJSON", "矢量专题" -> "GEO_ENTITY";
            case "GEO_ENTITY", "基础地理实体数据" -> "GEO_ENTITY";
            case "OSGB", "倾斜摄影三维", "MESH", "倾斜摄影MESH三维模型" -> "MESH";
            case "POINT_CLOUD", "点云", "激光点云", "激光点云数据" -> "POINT_CLOUD";
            default -> "OTHER";
        };
    }

    public static String toDbCode(String uiKind) {
        if (uiKind == null || uiKind.isBlank()) {
            return "DLG";
        }
        String key = uiKind.trim();
        return switch (key) {
            case "DLG", "数字线划图", "数字线划地图" -> "DLG";
            case "DOM", "数字正射影像" -> "DOM";
            case "DEM", "数字高程模型" -> "DEM";
            case "DRG", "数字栅格地图" -> "DRG";
            case "GeoTIFF", "遥感影像" -> "DOM";
            case "SHP/GeoJSON", "SHP_GEOJSON", "矢量专题", "GEO_ENTITY", "基础地理实体数据" -> "GEO_ENTITY";
            case "OSGB", "MESH", "倾斜摄影三维", "倾斜摄影Mesh三维模型" -> "MESH";
            case "点云", "POINT_CLOUD", "激光点云", "激光点云数据" -> "POINT_CLOUD";
            default -> {
                String normalized = normalizeDbCode(key);
                yield "OTHER".equals(normalized) ? "OTHER" : normalized;
            }
        };
    }

    public static String toUiLabel(String dbKind) {
        Def def = byDbCode(dbKind);
        if (def != null) {
            return def.uiLabel();
        }
        if (dbKind == null || dbKind.isBlank() || "OTHER".equalsIgnoreCase(dbKind)) {
            return "其他";
        }
        return dbKind;
    }

    public static String inferUiKind(String fileName) {
        if (fileName == null || fileName.isBlank()) {
            return "DLG";
        }
        String lower = fileName.toLowerCase(Locale.ROOT);
        int dot = lower.lastIndexOf('.');
        String ext = dot >= 0 ? lower.substring(dot + 1) : "";
        return switch (ext) {
            case "dlg", "dxf" -> "DLG";
            case "tif", "tiff", "img", "sid", "jp2" -> "DOM";
            case "dem", "asc", "bil", "hgt" -> "DEM";
            case "drg" -> "DRG";
            case "shp", "geojson", "json", "gpkg", "gdb" -> "基础地理实体数据";
            case "osgb", "obj", "gltf", "glb", "3mx", "s3c" -> "倾斜摄影Mesh三维模型";
            case "las", "laz", "xyz", "e57", "pts" -> "激光点云数据";
            default -> "DLG";
        };
    }
}
