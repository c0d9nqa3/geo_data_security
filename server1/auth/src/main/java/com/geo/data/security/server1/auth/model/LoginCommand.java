package com.geo.data.security.server1.auth.model;

public record LoginCommand(String username, String password, String clientIp) {
}
