package com.geo.data.security.server1.app.dashboard;

import java.util.List;

public record DataVolumeOverviewDto(
        String granularity,
        int year,
        List<Integer> years,
        long countThreshold,
        long bytesThreshold,
        long totalCount,
        long totalBytes,
        long unclassifiedCount,
        long unclassifiedBytes,
        boolean countAlert,
        boolean bytesAlert,
        List<DataKindVolumeDto> kinds
) {
}
