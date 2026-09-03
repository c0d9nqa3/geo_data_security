package com.geo.data.security.server1.audit.service;

import com.geo.data.security.server1.audit.model.AuditEventCommand;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
@ConditionalOnProperty(name = "gateway.business-store", havingValue = "stub")
public class InMemoryAuditRecorder implements AuditRecorder {

    private final List<AuditEventCommand> events = new CopyOnWriteArrayList<>();

    @Override
    public void record(AuditEventCommand command) {
        events.add(command);
    }

    public List<AuditEventCommand> recorded() {
        return new ArrayList<>(events);
    }
}
