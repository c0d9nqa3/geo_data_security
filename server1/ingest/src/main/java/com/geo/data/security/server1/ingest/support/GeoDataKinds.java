package com.geo.data.security.server1.ingest.support;

import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 工作台体量分析用的七类测绘数据。名称待客户确认后只改这一处即可同步上传与统计。
 */
public final class GeoDataKinds {

    public record Def(String dbCode, String uiLabel, String title, String color) {
    }

    public static final List<Def> ALL = List.of(
            new Def("GeoTIFF", "GeoTIFF", "遥感影像", "#22d3ee"),
            new Def("DOM", "DOM", "数字正射影像", "#3b82f6"),
            new Def("DEM", "DEM", "数字高程模型", "#10b981"),
            new Def("DLG", "DLG", "数字线划图", "#a855f7"),
            new Def("SHP_GEOJSON", "SHP/GeoJSON", "矢量专题", "#f59e0b"),
            new Def("OSGB", "OSGB", "倾斜摄影三维", "#fb923c"),
            new Def("POINT_CLOUD", "点云", "激光点云", "#818cf8")
    );

    private static final Map<String, Def> BY_DB = ALL.stream()
            .collect(Collectors.toUnmodifiableMap(d -> d.dbCode().toUpperCase(Locale.ROOT), Function.identity()));

    private GeoDataKinds() {
    }

    public static Def byDbCode(String dbCode) {
        if (dbCode == null || dbCode.isBlank()) {
            return null;
        }
        return BY_DB.get(dbCode.toUpperCase(Locale.ROOT));
    }

    public static String toDbCode(String uiKind) {
        if (uiKind == null || uiKind.isBlank()) {
            return "GeoTIFF";
        }
        String key = uiKind.trim();
        return switch (key) {
            case "GeoTIFF", "遥感影像" -> "GeoTIFF";
            case "DOM", "数字正射影像" -> "DOM";
            case "DEM", "数字高程模型" -> "DEM";
            case "DLG", "数字线划图" -> "DLG";
            case "SHP/GeoJSON", "SHP_GEOJSON", "矢量专题" -> "SHP_GEOJSON";
            case "OSGB", "倾斜摄影三维" -> "OSGB";
            case "点云", "POINT_CLOUD", "激光点云" -> "POINT_CLOUD";
            default -> "OTHER";
        };
    }

    public static String toUiLabel(String dbKind) {
        Def def = byDbCode(dbKind);
        if (def != null) {
            return def.uiLabel();
        }
        if (dbKind == null || dbKind.isBlank()) {
            return "其他";
        }
        return "OTHER".equalsIgnoreCase(dbKind) ? "其他" : dbKind;
    }

    public static String inferUiKind(String fileName) {
        if (fileName == null || fileName.isBlank()) {
            return "GeoTIFF";
        }
        String lower = fileName.toLowerCase(Locale.ROOT);
        int dot = lower.lastIndexOf('.');
        String ext = dot >= 0 ? lower.substring(dot + 1) : "";
        return switch (ext) {
            case "tif", "tiff" -> "GeoTIFF";
            case "img", "sid" -> "DOM";
            case "dem", "asc", "bil", "hgt" -> "DEM";
            case "dlg" -> "DLG";
            case "shp", "geojson", "json", "gpkg" -> "SHP/GeoJSON";
            case "osgb", "obj", "gltf", "glb" -> "OSGB";
            case "las", "laz", "xyz", "e57" -> "点云";
            default -> "GeoTIFF";
        };
    }
}
