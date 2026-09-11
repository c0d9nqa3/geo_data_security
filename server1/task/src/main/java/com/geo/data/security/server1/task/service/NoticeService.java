package com.geo.data.security.server1.task.service;

import com.geo.data.security.server1.common.web.PageDto;
import com.geo.data.security.server1.task.controller.dto.NoticeDto;
import com.geo.data.security.server1.task.controller.dto.NoticeUnreadDto;

public interface NoticeService {

    PageDto<NoticeDto> listNotices(Integer page, Integer pageSize);

    NoticeUnreadDto unreadCount();

    NoticeDto markRead(String noticeId);

    NoticeUnreadDto markAllRead();
}
