package com.geo.data.security.server1.app.dashboard;

import java.util.List;

public record DataKindVolumeDto(
        String code,
        String label,
        String title,
        String color,
        long totalCount,
        long totalBytes,
        long periodCount,
        long periodBytes,
        boolean countAlert,
        boolean bytesAlert,
        List<DataVolumePoint> points
) {
}
