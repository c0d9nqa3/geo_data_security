package com.geo.data.security.server1.ingest.controller.dto;

public record FileVolumeRow(String dataKind, int year, int month, long count, long bytes) {
}
