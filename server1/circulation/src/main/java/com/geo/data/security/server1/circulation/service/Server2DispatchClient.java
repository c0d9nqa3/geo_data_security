package com.geo.data.security.server1.circulation.service;

public interface Server2DispatchClient {

    boolean enabled();

    Server2DispatchResult dispatch(Server2DispatchCommand command);

    Server2TraceSnapshot queryTrace(String taskId, String resultId);
}
