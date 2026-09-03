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
                .andExpect(jsonPath("$.data[0].id").exists());
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
        mockMvc.perform(get("/api/circulations").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items").isArray())
                .andExpect(jsonPath("$.data.items.length()").value(0))
                .andExpect(jsonPath("$.data.total").value(0));

        mockMvc.perform(post("/api/circulations/cir_5001/approve")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"comment\":\"越权审批\"}"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("GW-403"));
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
    void createProjectOpensPendingTicketForAdminOnly() throws Exception {
        String operator = login("operator", "operator123");
        mockMvc.perform(post("/api/projects")
                        .header("Authorization", "Bearer " + operator)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"待审测试项目\",\"code\":\"REV-2026-01\",\"description\":\"自动进流转\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("draft"));

        mockMvc.perform(get("/api/circulations").header("Authorization", "Bearer " + operator))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items.length()").value(0));

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
