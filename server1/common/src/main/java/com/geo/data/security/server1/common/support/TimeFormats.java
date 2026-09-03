package com.geo.data.security.server1.common.support;

import java.sql.Timestamp;
import java.time.format.DateTimeFormatter;

public final class TimeFormats {

    public static final DateTimeFormatter DISPLAY = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");

    private TimeFormats() {
    }

    public static String format(Timestamp ts) {
        if (ts == null) {
            return "";
        }
        return DISPLAY.format(ts.toLocalDateTime());
    }

    public static String nullToEmpty(String value) {
        return value == null ? "" : value;
    }
}
