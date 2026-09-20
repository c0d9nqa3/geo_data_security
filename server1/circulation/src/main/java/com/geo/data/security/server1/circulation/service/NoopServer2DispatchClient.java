package com.geo.data.security.server1.circulation.service;

import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnMissingBean(Server2DispatchClient.class)
public class NoopServer2DispatchClient implements Server2DispatchClient {

    @Override
    public boolean enabled() {
        return false;
    }

    @Override
    public Server2DispatchResult dispatch(Server2DispatchCommand command) {
        return new Server2DispatchResult("", "", "skipped", "", "", "", "");
    }

    @Override
    public Server2TraceSnapshot queryTrace(String taskId, String resultId) {
        return Server2TraceSnapshot.unavailable("未连接服务器2");
    }
}
