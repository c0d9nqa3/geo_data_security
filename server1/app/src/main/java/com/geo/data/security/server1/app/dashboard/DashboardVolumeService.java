package com.geo.data.security.server1.app.dashboard;

import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.ingest.controller.dto.FileVolumeRow;
import com.geo.data.security.server1.ingest.service.FileIngestService;
import com.geo.data.security.server1.ingest.support.GeoDataKinds;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeSet;

@Service
public class DashboardVolumeService {

    public static final long COUNT_THRESHOLD = 10_000L;
    public static final long BYTES_THRESHOLD = 10L * 1024 * 1024 * 1024;
    private static final ZoneId ZONE = ZoneId.of("Asia/Shanghai");

    private final FileIngestService fileIngestService;

    public DashboardVolumeService(FileIngestService fileIngestService) {
        this.fileIngestService = fileIngestService;
    }

    public DataVolumeOverviewDto build(String granularityRaw, Integer yearRaw) {
        RequestContext.requirePrincipal();
        String granularity = "year".equalsIgnoreCase(granularityRaw) ? "year" : "month";
        LocalDate today = LocalDate.now(ZONE);
        List<FileVolumeRow> rows = fileIngestService.listVolumeRows();

        TreeSet<Integer> yearSet = new TreeSet<>();
        yearSet.add(today.getYear());
        for (FileVolumeRow row : rows) {
            if (row.year() > 0) {
                yearSet.add(row.year());
            }
        }
        int year = yearRaw == null ? today.getYear() : yearRaw;
        if (!yearSet.contains(year)) {
            year = today.getYear();
        }

        List<String> periods = new ArrayList<>();
        if ("year".equals(granularity)) {
            int from = Math.min(yearSet.first(), today.getYear() - 4);
            for (int y = from; y <= today.getYear(); y++) {
                periods.add(String.valueOf(y));
            }
        } else {
            for (int month = 1; month <= 12; month++) {
                periods.add("%d-%02d".formatted(year, month));
            }
        }
        Map<String, Integer> periodIndex = new HashMap<>();
        for (int i = 0; i < periods.size(); i++) {
            periodIndex.put(periods.get(i), i);
        }

        int kindCount = GeoDataKinds.ALL.size();
        long[][] counts = new long[kindCount][periods.size()];
        long[][] bytes = new long[kindCount][periods.size()];
        long[] totalCounts = new long[kindCount];
        long[] totalBytes = new long[kindCount];
        Map<String, Integer> kindIndex = new HashMap<>();
        for (int i = 0; i < kindCount; i++) {
            kindIndex.put(GeoDataKinds.ALL.get(i).dbCode().toUpperCase(Locale.ROOT), i);
        }

        long allCount = 0;
        long allBytes = 0;
        for (FileVolumeRow row : rows) {
            allCount += row.count();
            allBytes += row.bytes();
            Integer ki = kindIndex.get(GeoDataKinds.normalizeDbCode(row.dataKind()).toUpperCase(Locale.ROOT));
            if (ki == null) {
                continue;
            }
            totalCounts[ki] += row.count();
            totalBytes[ki] += row.bytes();
            String period = "year".equals(granularity)
                    ? String.valueOf(row.year())
                    : "%d-%02d".formatted(row.year(), Math.max(1, Math.min(12, row.month())));
            Integer pi = periodIndex.get(period);
            if (pi != null) {
                counts[ki][pi] += row.count();
                bytes[ki][pi] += row.bytes();
            }
        }

        List<DataKindVolumeDto> kinds = new ArrayList<>(kindCount);
        for (int i = 0; i < kindCount; i++) {
            GeoDataKinds.Def def = GeoDataKinds.ALL.get(i);
            List<DataVolumePoint> points = new ArrayList<>(periods.size());
            long periodCount = 0;
            long periodBytes = 0;
            for (int p = 0; p < periods.size(); p++) {
                points.add(new DataVolumePoint(periods.get(p), counts[i][p], bytes[i][p]));
                periodCount += counts[i][p];
                periodBytes += bytes[i][p];
            }
            kinds.add(new DataKindVolumeDto(
                    def.dbCode(),
                    def.uiLabel(),
                    def.title(),
                    def.color(),
                    totalCounts[i],
                    totalBytes[i],
                    periodCount,
                    periodBytes,
                    totalCounts[i] >= COUNT_THRESHOLD,
                    totalBytes[i] >= BYTES_THRESHOLD,
                    points
            ));
        }

        List<Integer> years = new ArrayList<>(yearSet.descendingSet());
        long classifiedCount = 0;
        long classifiedBytes = 0;
        for (int i = 0; i < kindCount; i++) {
            classifiedCount += totalCounts[i];
            classifiedBytes += totalBytes[i];
        }
        return new DataVolumeOverviewDto(
                granularity,
                year,
                years,
                COUNT_THRESHOLD,
                BYTES_THRESHOLD,
                allCount,
                allBytes,
                Math.max(0, allCount - classifiedCount),
                Math.max(0, allBytes - classifiedBytes),
                allCount >= COUNT_THRESHOLD,
                allBytes >= BYTES_THRESHOLD,
                kinds
        );
    }
}
