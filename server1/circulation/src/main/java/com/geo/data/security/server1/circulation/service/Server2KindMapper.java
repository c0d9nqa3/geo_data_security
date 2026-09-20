package com.geo.data.security.server1.circulation.service;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

public final class Server2KindMapper {

    public record Mapping(String dataType, String classification) {
    }

    private Server2KindMapper() {
    }

    public static Mapping map(String dataKind, String fileName) {
        String kind = dataKind == null ? "" : dataKind.trim().toUpperCase(Locale.ROOT);
        String ext = extension(fileName);
        return switch (kind) {
            case "DLG" -> new Mapping("DLG", "DLG_LINEWORK");
            case "DOM", "GEOTIFF" -> new Mapping("DOM", "ORTHOIMAGE");
            case "DEM" -> new Mapping("DEM", "ELEVATION_DEM");
            case "DRG" -> new Mapping("DRG", "ORTHOIMAGE");
            case "GEO_ENTITY", "SHP_GEOJSON" -> ext.equals("geojson") || ext.equals("json")
                    ? new Mapping("GEOJSON", "THEMATIC_VECTOR")
                    : new Mapping("SHP", "THEMATIC_VECTOR");
            case "MESH", "OSGB" -> new Mapping("MESH", "OBLIQUE_MESH");
            case "POINT_CLOUD" -> new Mapping("POINT_CLOUD", "POINT_CLOUD");
            default -> extSwitch(ext);
        };
    }

    public static String watermark(String dataType, String projectId) {
        String type = dataType == null ? "" : dataType.toUpperCase(Locale.ROOT);
        if (type.equals("DLG") || type.equals("SHP") || type.equals("GEOJSON")) {
            String project = projectId == null || projectId.isBlank() ? "PROJECT" : projectId.trim();
            return "DLG-" + project;
        }
        return "0x" + LocalDate.now().format(DateTimeFormatter.BASIC_ISO_DATE);
    }

    private static Mapping extSwitch(String ext) {
        return switch (ext) {
            case "tif", "tiff", "img", "jp2" -> new Mapping("DOM", "ORTHOIMAGE");
            case "dem", "asc", "bil", "hgt" -> new Mapping("DEM", "ELEVATION_DEM");
            case "shp", "gpkg", "gdb", "zip" -> new Mapping("SHP", "THEMATIC_VECTOR");
            case "geojson", "json" -> new Mapping("GEOJSON", "THEMATIC_VECTOR");
            case "osgb", "obj", "gltf", "glb", "3mx" -> new Mapping("MESH", "OBLIQUE_MESH");
            case "las", "laz", "e57", "pts" -> new Mapping("POINT_CLOUD", "POINT_CLOUD");
            default -> new Mapping("DOM", "ORTHOIMAGE");
        };
    }

    private static String extension(String fileName) {
        if (fileName == null) {
            return "";
        }
        int dot = fileName.lastIndexOf('.');
        return dot < 0 ? "" : fileName.substring(dot + 1).toLowerCase(Locale.ROOT);
    }
}
