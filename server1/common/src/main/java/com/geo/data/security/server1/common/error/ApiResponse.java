package com.geo.data.security.server1.common.error;

import com.fasterxml.jackson.annotation.JsonInclude;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class ApiResponse<T> {

    private final String code;
    private final String message;
    private final boolean retryable;
    private final String requestId;
    private final T data;

    private ApiResponse(String code, String message, boolean retryable, String requestId, T data) {
        this.code = code;
        this.message = message;
        this.retryable = retryable;
        this.requestId = requestId;
        this.data = data;
    }

    public static <T> ApiResponse<T> ok(String requestId, T data) {
        return new ApiResponse<>(ErrorCode.OK.getCode(), ErrorCode.OK.getMessage(), false, requestId, data);
    }

    public static <T> ApiResponse<T> fail(ErrorCode error, String requestId) {
        return new ApiResponse<>(error.getCode(), error.getMessage(), error.isRetryable(), requestId, null);
    }

    public static <T> ApiResponse<T> fail(ErrorCode error, String requestId, String message) {
        return new ApiResponse<>(error.getCode(), message, error.isRetryable(), requestId, null);
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

    public String getRequestId() {
        return requestId;
    }

    public T getData() {
        return data;
    }
}
