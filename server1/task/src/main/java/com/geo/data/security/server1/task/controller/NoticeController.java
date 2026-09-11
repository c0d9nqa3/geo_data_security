package com.geo.data.security.server1.task.controller;

import com.geo.data.security.server1.common.context.RequestContext;
import com.geo.data.security.server1.common.error.ApiResponse;
import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.task.controller.dto.NoticeDto;
import com.geo.data.security.server1.task.controller.dto.NoticeUnreadDto;
import com.geo.data.security.server1.task.service.NoticeService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/notices")
public class NoticeController {

    private final NoticeService noticeService;

    public NoticeController(NoticeService noticeService) {
        this.noticeService = noticeService;
    }

    @GetMapping
    public ApiResponse<PageDto<NoticeDto>> list(
            @RequestParam(value = "page", required = false) Integer page,
            @RequestParam(value = "pageSize", required = false) Integer pageSize) {
        return ApiResponse.ok(RequestContext.requestId(), noticeService.listNotices(page, pageSize));
    }

    @GetMapping("/unread-count")
    public ApiResponse<NoticeUnreadDto> unreadCount() {
        return ApiResponse.ok(RequestContext.requestId(), noticeService.unreadCount());
    }

    @PostMapping("/read-all")
    public ApiResponse<NoticeUnreadDto> readAll() {
        return ApiResponse.ok(RequestContext.requestId(), noticeService.markAllRead());
    }

    @PostMapping("/{id}/read")
    public ApiResponse<NoticeDto> read(@PathVariable("id") String id) {
        return ApiResponse.ok(RequestContext.requestId(), noticeService.markRead(id));
    }
}
