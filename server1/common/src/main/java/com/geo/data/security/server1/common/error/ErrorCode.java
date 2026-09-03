package com.geo.data.security.server1.common.error;

/**
 * 统一错误码。消息不得泄露真实路径、密钥、数据库连接信息。
 */
public enum ErrorCode {
    OK("0", "成功", false),
    BAD_REQUEST("GW-400", "请求参数不合法", false),
    UNAUTHORIZED("GW-401", "未登录或令牌无效", false),
    FORBIDDEN("GW-403", "无权访问该资源", false),
    NOT_FOUND("GW-404", "资源不存在", false),
    METHOD_NOT_ALLOWED("GW-405", "方法不允许", false),
    PAYLOAD_TOO_LARGE("GW-413", "请求体过大", false),
    TOO_MANY_REQUESTS("GW-429", "请求过于频繁，请稍后重试", true),
    INTERNAL_ERROR("GW-500", "服务内部错误", true),
    SERVICE_UNAVAILABLE("GW-503", "服务暂不可用", true),
    PATH_BLOCKED("GW-4031", "禁止访问的路径", false),
    UPSTREAM_NOT_READY("GW-5031", "下游业务模块尚未就绪", true);

    private final String code;
    private final String message;
    private final boolean retryable;

    ErrorCode(String code, String message, boolean retryable) {
        this.code = code;
        this.message = message;
        this.retryable = retryable;
    }

    public String getCode() {
        return code;
    }

    public String getMessage() {
        return message;
    }

    public boolean isRetryable() {
        return retryable;
    }
}
