package com.geo.data.security.server1.app;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class Server1ApplicationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void healthShouldBePublic() throws Exception {
        mockMvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value("0"))
                .andExpect(jsonPath("$.data.status").value("UP"));
    }

    @Test
    void projectsShouldRequireAuth() throws Exception {
        mockMvc.perform(get("/api/projects"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("GW-401"));
    }

    @Test
    void loginAndAccessProjects() throws Exception {
        String body = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"admin\",\"password\":\"admin123\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.token").isNotEmpty())
                .andReturn()
                .getResponse()
                .getContentAsString();

        String token = body.replaceAll("(?s).*\"token\"\\s*:\\s*\"([^\"]+)\".*", "$1");

        mockMvc.perform(get("/api/projects").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value("0"))
                .andExpect(jsonPath("$.data.items[0].id").exists())
                .andExpect(jsonPath("$.data.total").isNumber())
                .andExpect(jsonPath("$.data.page").value(1));
    }

    @Test
    void logoutShouldInvalidateToken() throws Exception {
        String body = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"admin\",\"password\":\"admin123\"}"))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        String token = body.replaceAll("(?s).*\"token\"\\s*:\\s*\"([^\"]+)\".*", "$1");

        mockMvc.perform(post("/api/auth/logout").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk());

        mockMvc.perform(get("/api/projects").header("Authorization", "Bearer " + token))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void blockedPathShouldBeForbidden() throws Exception {
        mockMvc.perform(get("/api/server2/raw"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("GW-4031"));
    }

    @Test
    void operatorCannotApproveCirculation() throws Exception {
        String token = login("operator", "operator123");
        mockMvc.perform(post("/api/circulations/cir_5001/approve")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"comment\":\"越权审批\"}"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("GW-403"));
        mockMvc.perform(post("/api/circulations/cir_5001/distribute")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isForbidden());
    }

    @Test
    void staffCanDistributeOwnApprovedTicket() throws Exception {
        String zhangsan = login("zhangsan", "zhangsan123");
        mockMvc.perform(post("/api/projects")
                        .header("Authorization", "Bearer " + zhangsan)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"张三分发项目\",\"code\":\"ZS-DIST-01\",\"description\":\"审核后由本人分发\"}"))
                .andExpect(status().isOk());

        String listBody = mockMvc.perform(get("/api/circulations").header("Authorization", "Bearer " + zhangsan))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        String id = listBody.replaceAll("(?s).*?\"id\"\\s*:\\s*\"(cir_[^\"]+)\".*", "$1");

        mockMvc.perform(post("/api/circulations/" + id + "/approve")
                        .header("Authorization", "Bearer " + zhangsan)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"comment\":\"员工越权审批\"}"))
                .andExpect(status().isForbidden());
        mockMvc.perform(post("/api/circulations/" + id + "/distribute")
                        .header("Authorization", "Bearer " + zhangsan))
                .andExpect(status().isBadRequest());

        String admin = login("admin", "admin123");
        mockMvc.perform(post("/api/circulations/" + id + "/approve")
                        .header("Authorization", "Bearer " + admin)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"comment\":\"审核通过，交由提交人分发\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("approved"));

        String lisi = login("lisi", "lisi123");
        mockMvc.perform(post("/api/circulations/" + id + "/distribute")
                        .header("Authorization", "Bearer " + lisi))
                .andExpect(status().isForbidden());

        mockMvc.perform(post("/api/circulations/" + id + "/distribute")
                        .header("Authorization", "Bearer " + zhangsan))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.distributeStatus").value("dispatched"));
    }

    @Test
    void adminCanReviewCirculation() throws Exception {
        String token = login("admin", "admin123");
        mockMvc.perform(get("/api/circulations/cir_5001").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.id").value("cir_5001"))
                .andExpect(jsonPath("$.data.applyType").value("task"))
                .andExpect(jsonPath("$.data.status").value("pending"));

        mockMvc.perform(post("/api/circulations/cir_5001/approve")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"comment\":\"同意外发\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("approved"));

        mockMvc.perform(post("/api/circulations/cir_5001/distribute")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.distributeStatus").value("dispatched"));
    }

    @Test
    void staffCanSeeOwnPendingTicketButCannotApprove() throws Exception {
        String zhangsan = login("zhangsan", "zhangsan123");
        mockMvc.perform(post("/api/projects")
                        .header("Authorization", "Bearer " + zhangsan)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"张三待审项目\",\"code\":\"ZS-2026-01\",\"description\":\"本人可见\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("draft"));

        mockMvc.perform(get("/api/circulations").header("Authorization", "Bearer " + zhangsan))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[?(@.applyType == 'project')]").isNotEmpty());

        String lisi = login("lisi", "lisi123");
        mockMvc.perform(get("/api/projects").header("Authorization", "Bearer " + lisi))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[?(@.code == 'ZS-2026-01')]").isEmpty());
        mockMvc.perform(get("/api/circulations").header("Authorization", "Bearer " + lisi))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[?(@.applyUser == '张三')]").isEmpty());

        String admin = login("admin", "admin123");
        mockMvc.perform(get("/api/circulations").header("Authorization", "Bearer " + admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[?(@.applyType == 'project')]").isNotEmpty());
    }

    @Test
    void adminCanLogicallyDeleteCirculation() throws Exception {
        String operator = login("operator", "operator123");
        mockMvc.perform(post("/api/projects")
                        .header("Authorization", "Bearer " + operator)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"待删项目\",\"code\":\"DEL-2026-01\",\"description\":\"逻辑删除\"}"))
                .andExpect(status().isOk());

        String admin = login("admin", "admin123");
        String listBody = mockMvc.perform(get("/api/circulations").header("Authorization", "Bearer " + admin))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        String id = listBody.replaceAll("(?s).*?\"id\"\\s*:\\s*\"(cir_[^\"]+)\".*", "$1");

        mockMvc.perform(post("/api/circulations/" + id + "/delete")
                        .header("Authorization", "Bearer " + admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value("0"));

        mockMvc.perform(get("/api/circulations/" + id).header("Authorization", "Bearer " + admin))
                .andExpect(status().isNotFound());
    }

    @Test
    void circulationListShouldPaginate() throws Exception {
        String token = login("admin", "admin123");
        mockMvc.perform(get("/api/circulations").param("page", "1").param("pageSize", "1")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.page").value(1))
                .andExpect(jsonPath("$.data.pageSize").value(1))
                .andExpect(jsonPath("$.data.items.length()").value(1))
                .andExpect(jsonPath("$.data.total").isNumber())
                .andExpect(jsonPath("$.data.totalPages").isNumber());
    }

    @Test
    void projectFileTaskListsShouldPaginate() throws Exception {
        String token = login("admin", "admin123");
        mockMvc.perform(get("/api/projects").param("page", "1").param("pageSize", "1")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items").isArray())
                .andExpect(jsonPath("$.data.pageSize").value(1))
                .andExpect(jsonPath("$.data.totalPages").isNumber());
        mockMvc.perform(get("/api/files").param("page", "1").param("pageSize", "1")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items").isArray())
                .andExpect(jsonPath("$.data.pageSize").value(1));
        mockMvc.perform(get("/api/tasks").param("page", "1").param("pageSize", "1")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items").isArray())
                .andExpect(jsonPath("$.data.pageSize").value(1))
                .andExpect(jsonPath("$.data.items[0].stage").isNotEmpty());
        mockMvc.perform(get("/api/tasks/task_3001").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.id").value("task_3001"))
                .andExpect(jsonPath("$.data.outputReady").value(true));
        mockMvc.perform(post("/api/tasks/task_3001/download").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.resultId").value("res_4001"));
        mockMvc.perform(get("/api/audit/events").param("page", "1").param("pageSize", "1")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items").isArray())
                .andExpect(jsonPath("$.data.page").value(1))
                .andExpect(jsonPath("$.data.pageSize").value(1))
                .andExpect(jsonPath("$.data.total").isNumber())
                .andExpect(jsonPath("$.data.totalPages").isNumber());
    }

    @Test
    void circulationApplyEndpointIsDisabled() throws Exception {
        String token = login("operator", "operator123");
        mockMvc.perform(post("/api/circulations")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"projectId\":\"prj_1001\",\"taskId\":\"task_3001\",\"purpose\":\"x\",\"authorizeScope\":\"self\",\"expireHours\":24}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void uploadShouldAcceptLocalMultipartFile() throws Exception {
        String token = login("operator", "operator123");
        MockMultipartFile file = new MockMultipartFile(
                "file", "tile_B01.tif", "image/tiff", "demo-bytes".getBytes());
        mockMvc.perform(multipart("/api/files/upload")
                        .file(file)
                        .param("projectId", "prj_1001")
                        .param("kind", "GeoTIFF")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value("0"))
                .andExpect(jsonPath("$.data.name").value("tile_B01.tif"))
                .andExpect(jsonPath("$.data.kind").value("GeoTIFF"))
                .andExpect(jsonPath("$.data.status").value("uploaded"))
                .andExpect(jsonPath("$.data.hash").value("sha256:demo"))
                .andExpect(jsonPath("$.data.uploadedBy").isNotEmpty())
                .andExpect(jsonPath("$.data.uploadedAt").isNotEmpty());
    }

    @Test
    void staffCanReadDashboardAndAudit() throws Exception {
        String token = login("zhangsan", "zhangsan123");
        mockMvc.perform(get("/api/dashboard/overview").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.projectCount").isNumber())
                .andExpect(jsonPath("$.data.fileCount").isNumber())
                .andExpect(jsonPath("$.data.recentTasks").isArray())
                .andExpect(jsonPath("$.data.recentAudits").isArray())
                .andExpect(jsonPath("$.data.taskTrend.length()").value(7))
                .andExpect(jsonPath("$.data.auditTrend.length()").value(7));
        mockMvc.perform(get("/api/audit/events").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items").isArray());
    }

    @Test
    void reviewerShouldReceiveUrgeNotice() throws Exception {
        String admin = login("admin", "admin123");
        mockMvc.perform(post("/api/notices/read-all").header("Authorization", "Bearer " + admin))
                .andExpect(status().isOk());

        String zhangsan = login("zhangsan", "zhangsan123");
        mockMvc.perform(post("/api/tasks/cir_zs_pending/urge")
                        .header("Authorization", "Bearer " + zhangsan))
                .andExpect(status().isOk());

        mockMvc.perform(get("/api/notices/unread-count").header("Authorization", "Bearer " + zhangsan))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.unreadCount").value(0));

        mockMvc.perform(get("/api/notices/unread-count").header("Authorization", "Bearer " + admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.unreadCount").value(1));
        mockMvc.perform(get("/api/notices").header("Authorization", "Bearer " + admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[0].type").value("urge"))
                .andExpect(jsonPath("$.data.items[0].senderName").value("张三"))
                .andExpect(jsonPath("$.data.items[0].circulationId").value("cir_zs_pending"))
                .andExpect(jsonPath("$.data.items[0].read").value(false))
                .andExpect(jsonPath("$.data.items[0].content").value(org.hamcrest.Matchers.containsString("催办")));

        String noticeId = mockMvc.perform(get("/api/notices").header("Authorization", "Bearer " + admin))
                .andReturn()
                .getResponse()
                .getContentAsString()
                .replaceAll("(?s).*?\"id\"\\s*:\\s*\"(ntc_[^\"]+)\".*", "$1");
        mockMvc.perform(post("/api/notices/" + noticeId + "/read").header("Authorization", "Bearer " + admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.read").value(true));
        mockMvc.perform(get("/api/notices/unread-count").header("Authorization", "Bearer " + admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.unreadCount").value(0));
    }

    private String login(String username, String password) throws Exception {
        String body = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"" + username + "\",\"password\":\"" + password + "\"}"))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        return body.replaceAll("(?s).*\"token\"\\s*:\\s*\"([^\"]+)\".*", "$1");
    }
}
