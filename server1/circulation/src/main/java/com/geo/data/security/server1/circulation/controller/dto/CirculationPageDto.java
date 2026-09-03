package com.geo.data.security.server1.circulation.controller.dto;

import java.util.List;

public record CirculationPageDto(
        List<CirculationDto> items,
        long total,
        int page,
        int pageSize,
        int totalPages
) {
    public static int normalizeSize(Integer pageSize) {
        int size = pageSize == null ? 10 : pageSize;
        if (size < 1) {
            return 1;
        }
        if (size > 100) {
            return 100;
        }
        return size;
    }

    public static int totalPages(long total, int pageSize) {
        if (total <= 0) {
            return 1;
        }
        return (int) ((total + pageSize - 1) / pageSize);
    }

    public static int normalizePage(Integer page, int totalPages) {
        int current = page == null || page < 1 ? 1 : page;
        return Math.min(current, Math.max(totalPages, 1));
    }

    public static CirculationPageDto slice(List<CirculationDto> all, Integer page, Integer pageSize) {
        int size = normalizeSize(pageSize);
        long total = all.size();
        int pages = totalPages(total, size);
        int current = normalizePage(page, pages);
        int from = (current - 1) * size;
        List<CirculationDto> items = from >= all.size()
                ? List.of()
                : List.copyOf(all.subList(from, Math.min(from + size, all.size())));
        return new CirculationPageDto(items, total, current, size, pages);
    }
}
