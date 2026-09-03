package com.geo.data.security.server1.circulation.controller;

import com.geo.data.security.server1.circulation.controller.dto.CirculationDto;
import com.geo.data.security.server1.circulation.controller.dto.CirculationPageDto;
import com.geo.data.security.server1.circulation.controller.dto.CreateCirculationRequest;
import com.geo.data.security.server1.circulation.controller.dto.ReviewActionRequest;
import com.geo.data.security.server1.circulation.service.CirculationService;
import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiResponse;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/circulations")
public class CirculationController {

    private final CirculationService circulationService;

    public CirculationController(CirculationService circulationService) {
        this.circulationService = circulationService;
    }

    @GetMapping
    public ApiResponse<CirculationPageDto> list(
            @RequestParam(value = "status", required = false) String status,
            @RequestParam(value = "page", required = false) Integer page,
            @RequestParam(value = "pageSize", required = false) Integer pageSize) {
        return ApiResponse.ok(RequestContext.requestId(),
                circulationService.listCirculations(status, page, pageSize));
    }

    @GetMapping("/{id}")
    public ApiResponse<CirculationDto> detail(@PathVariable("id") String id) {
        return ApiResponse.ok(RequestContext.requestId(), circulationService.getCirculation(id));
    }

    @PostMapping
    public ApiResponse<CirculationDto> apply(@Valid @RequestBody CreateCirculationRequest request) {
        return ApiResponse.ok(RequestContext.requestId(), circulationService.apply(request));
    }

    @PostMapping("/{id}/approve")
    public ApiResponse<CirculationDto> approve(
            @PathVariable("id") String id,
            @RequestBody(required = false) ReviewActionRequest request) {
        return ApiResponse.ok(RequestContext.requestId(),
                circulationService.approve(id, request == null ? new ReviewActionRequest("") : request));
    }

    @PostMapping("/{id}/reject")
    public ApiResponse<CirculationDto> reject(
            @PathVariable("id") String id,
            @RequestBody(required = false) ReviewActionRequest request) {
        return ApiResponse.ok(RequestContext.requestId(),
                circulationService.reject(id, request == null ? new ReviewActionRequest("") : request));
    }

    @PostMapping("/{id}/distribute")
    public ApiResponse<CirculationDto> distribute(@PathVariable("id") String id) {
        return ApiResponse.ok(RequestContext.requestId(), circulationService.distribute(id));
    }

    @PostMapping("/{id}/delete")
    public ApiResponse<Void> delete(@PathVariable("id") String id) {
        circulationService.deleteCirculation(id);
        return ApiResponse.ok(RequestContext.requestId(), null);
    }
}
