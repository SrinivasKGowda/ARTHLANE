package com.arthlane;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.ResultActions;

import com.arthlane.auth.Totp;
import com.jayway.jsonpath.JsonPath;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class ApiFlowTest {

    @Autowired
    MockMvc mvc;

    @Autowired
    JdbcTemplate jdbc;

    private ResultActions postJson(String url, String json, String token) throws Exception {
        var request = post(url).contentType(MediaType.APPLICATION_JSON).content(json);
        return mvc.perform(token == null ? request : request.header("Authorization", "Bearer " + token));
    }

    private static String read(MvcResult result, String path) throws Exception {
        Object value = JsonPath.read(result.getResponse().getContentAsString(), path);
        return value == null ? null : String.valueOf(value);
    }

    private String requestCode(String destination) throws Exception {
        return read(postJson("/api/v1/auth/otp/request", "{\"destination\":\"" + destination + "\"}", null)
                .andExpect(status().isOk()).andReturn(), "$.devCode");
    }

    /** Lets a test ask for a second code without waiting out the resend cooldown. */
    private void ageCodes(String destination) {
        jdbc.update("update otp_challenges set created_at = ? where destination = ?",
                OffsetDateTime.now(ZoneOffset.UTC).minusMinutes(2), destination);
    }

    private MvcResult signIn(String destination) throws Exception {
        String code = requestCode(destination);
        return postJson("/api/v1/auth/otp/verify", "{\"destination\":\"" + destination + "\",\"code\":\"" + code + "\"}", null)
                .andExpect(status().isOk()).andReturn();
    }

    @Test
    void otpSignInProfileAndTokenRotation() throws Exception {
        MvcResult sent = postJson("/api/v1/auth/otp/request", "{\"destination\":\"98765 43210\"}", null)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.destination").value("+919876543210"))
                .andExpect(jsonPath("$.expiresIn").value(300))
                .andReturn();
        String code = read(sent, "$.devCode");

        postJson("/api/v1/auth/otp/request", "{\"destination\":\"9876543210\"}", null)
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.detail", containsString("seconds")));

        String wrong = code.equals("000000") ? "111111" : "000000";
        postJson("/api/v1/auth/otp/verify", "{\"destination\":\"9876543210\",\"code\":\"" + wrong + "\"}", null)
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.detail").value("Wrong code. 4 attempts left."));

        MvcResult signedIn = postJson("/api/v1/auth/otp/verify", "{\"destination\":\"+91 98765 43210\",\"code\":\"" + code + "\"}", null)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.twoFactorRequired").value(false))
                .andExpect(jsonPath("$.newUser").value(true))
                .andExpect(jsonPath("$.user.phone").value("+919876543210"))
                .andExpect(jsonPath("$.expiresIn").value(900))
                .andReturn();
        String access = read(signedIn, "$.accessToken");
        String refresh = read(signedIn, "$.refreshToken");

        postJson("/api/v1/auth/otp/verify", "{\"destination\":\"9876543210\",\"code\":\"" + code + "\"}", null)
                .andExpect(status().isBadRequest());

        mvc.perform(get("/api/v1/me")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/me").header("Authorization", "Bearer " + access))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.experience").value("Beginner"))
                .andExpect(jsonPath("$.segments", hasSize(2)))
                .andExpect(jsonPath("$.twoFactorEnabled").value(false));

        mvc.perform(put("/api/v1/me").header("Authorization", "Bearer " + access).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\" Srini \",\"style\":\"Positional\",\"capital\":250000,\"segments\":[\"Equity\",\"Crypto\"],\"newsMode\":\"30m\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("Srini"))
                .andExpect(jsonPath("$.style").value("Positional"))
                .andExpect(jsonPath("$.capital").value(250000))
                .andExpect(jsonPath("$.segments[1]").value("Crypto"));

        mvc.perform(put("/api/v1/me").header("Authorization", "Bearer " + access).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"risk\":\"YOLO\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail", containsString("risk")));

        String newRefresh = read(postJson("/api/v1/auth/refresh", "{\"refreshToken\":\"" + refresh + "\"}", null)
                .andExpect(status().isOk())
                .andReturn(), "$.refreshToken");

        postJson("/api/v1/auth/refresh", "{\"refreshToken\":\"" + refresh + "\"}", null)
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.detail", containsString("another tab")));
        String newest = read(postJson("/api/v1/auth/refresh", "{\"refreshToken\":\"" + newRefresh + "\"}", null)
                .andExpect(status().isOk())
                .andReturn(), "$.refreshToken");

        jdbc.update("update refresh_tokens set revoked_at = ? where rotated", OffsetDateTime.now(ZoneOffset.UTC).minusMinutes(1));
        postJson("/api/v1/auth/refresh", "{\"refreshToken\":\"" + newRefresh + "\"}", null)
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.detail", containsString("already used")));
        postJson("/api/v1/auth/refresh", "{\"refreshToken\":\"" + newest + "\"}", null)
                .andExpect(status().isUnauthorized());

        mvc.perform(get("/api/v1/me").header("Authorization", "Bearer not-a-token")).andExpect(status().isUnauthorized());
    }

    @Test
    void logoutEndsOnlyThatSession() throws Exception {
        String destination = "logout@example.in";
        String first = read(signIn(destination), "$.refreshToken");
        ageCodes(destination);
        MvcResult second = signIn(destination);
        String secondRefresh = read(second, "$.refreshToken");

        postJson("/api/v1/auth/logout", "{\"refreshToken\":\"" + first + "\"}", null).andExpect(status().isNoContent());
        postJson("/api/v1/auth/refresh", "{\"refreshToken\":\"" + first + "\"}", null).andExpect(status().isUnauthorized());
        String rotated = read(postJson("/api/v1/auth/refresh", "{\"refreshToken\":\"" + secondRefresh + "\"}", null)
                .andExpect(status().isOk()).andReturn(), "$.refreshToken");

        postJson("/api/v1/me/security/logout-all", "{}", read(second, "$.accessToken")).andExpect(status().isNoContent());
        postJson("/api/v1/auth/refresh", "{\"refreshToken\":\"" + rotated + "\"}", null).andExpect(status().isUnauthorized());
    }

    @Test
    void paperPositionsJournalAndStats() throws Exception {
        String access = read(signIn("trader@example.in"), "$.accessToken");

        String stock = "{\"clientRef\":\"p1\",\"kind\":\"eq\",\"symbol\":\"RELIANCE.NS\",\"label\":\"Reliance\",\"side\":\"B\",\"qty\":10,\"entry\":100,\"stop\":95,\"target\":110,\"openedAt\":1758000000000}";
        MvcResult opened = postJson("/api/v1/positions", stock, access)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.kind").value("eq"))
                .andExpect(jsonPath("$.openedAt").value(1758000000000L))
                .andReturn();
        String stockId = read(opened, "$.id");
        postJson("/api/v1/positions", stock, access).andExpect(jsonPath("$.id").value(Long.valueOf(stockId)));

        String option = "{\"clientRef\":\"p2\",\"kind\":\"opt\",\"label\":\"NIFTY 25000 CE\",\"side\":\"S\",\"entry\":120,\"optionType\":\"CE\",\"strike\":25000,\"expiry\":\"30-Sep-2026\",\"lots\":2,\"lotSize\":65}";
        String optionId = read(postJson("/api/v1/positions", option, access)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.symbol").value("^NSEI"))
                .andReturn(), "$.id");

        postJson("/api/v1/positions", "{\"kind\":\"opt\",\"label\":\"x\",\"side\":\"B\",\"entry\":10}", access)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail", containsString("option needs")));

        mvc.perform(get("/api/v1/positions").header("Authorization", "Bearer " + access))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)));

        postJson("/api/v1/positions/" + stockId + "/close", "{\"exitPrice\":110,\"clientRef\":\"j1\"}", access)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.pnl").value(100.0))
                .andExpect(jsonPath("$.units").value(10));
        postJson("/api/v1/positions/" + stockId + "/close", "{\"exitPrice\":110,\"clientRef\":\"j1\"}", access)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.pnl").value(100.0));
        postJson("/api/v1/positions/" + optionId + "/close", "{\"exitPrice\":100}", access)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.pnl").value(2600.0))
                .andExpect(jsonPath("$.units").value(130));

        postJson("/api/v1/journal", "{\"clientRef\":\"old1\",\"symbol\":\"BTC-USD\",\"label\":\"Bitcoin\",\"side\":\"B\",\"units\":0.01,\"entry\":60000,\"exit\":59000,\"pnl\":-850.4,\"openedAt\":1757000000000,\"closedAt\":1757100000000}", access)
                .andExpect(status().isOk());

        mvc.perform(get("/api/v1/journal").header("Authorization", "Bearer " + access))
                .andExpect(jsonPath("$", hasSize(3)))
                .andExpect(jsonPath("$[2].clientRef").value("old1"));

        mvc.perform(get("/api/v1/journal/stats").header("Authorization", "Bearer " + access))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.trades").value(3))
                .andExpect(jsonPath("$.wins").value(2))
                .andExpect(jsonPath("$.winRate").value(66.7))
                .andExpect(jsonPath("$.totalPnl").value(1849.6))
                .andExpect(jsonPath("$.worst").value(-850.4))
                .andExpect(jsonPath("$.profitFactor").value(3.17));

        String otherUser = read(signIn("someone@example.in"), "$.accessToken");
        mvc.perform(get("/api/v1/journal").header("Authorization", "Bearer " + otherUser)).andExpect(jsonPath("$", hasSize(0)));
        String entryId = read(mvc.perform(get("/api/v1/journal").header("Authorization", "Bearer " + access)).andReturn(), "$[0].id");
        mvc.perform(delete("/api/v1/journal/" + entryId).header("Authorization", "Bearer " + otherUser)).andExpect(status().isNotFound());
        mvc.perform(delete("/api/v1/journal/" + entryId).header("Authorization", "Bearer " + access)).andExpect(status().isNoContent());
        mvc.perform(get("/api/v1/journal/stats").header("Authorization", "Bearer " + otherUser))
                .andExpect(jsonPath("$.trades").value(0))
                .andExpect(jsonPath("$.winRate").value(nullValue()));
    }

    @Test
    void twoFactorSetupAndSignIn() throws Exception {
        String destination = "twofactor@example.in";
        String access = read(signIn(destination), "$.accessToken");

        String secret = read(postJson("/api/v1/me/security/2fa/setup", "{}", access)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.otpauthUri", containsString("otpauth://totp/Arthlane")))
                .andReturn(), "$.secret");
        byte[] key = Totp.base32Decode(secret);
        long step = Instant.now().getEpochSecond() / Totp.STEP_SECONDS;

        postJson("/api/v1/me/security/2fa/enable", "{\"code\":\"000000x\"}", access).andExpect(status().isUnauthorized());
        postJson("/api/v1/me/security/2fa/enable", "{\"code\":\"" + Totp.code(key, step, 6) + "\"}", access)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.enabled").value(true));

        ageCodes(destination);
        MvcResult pending = signIn(destination);
        String mfa = read(pending, "$.twoFactorToken");
        assertThat(read(pending, "$.twoFactorRequired")).isEqualTo("true");
        assertThat(read(pending, "$.accessToken")).isNull();

        mvc.perform(get("/api/v1/me").header("Authorization", "Bearer " + mfa)).andExpect(status().isForbidden());

        postJson("/api/v1/auth/2fa/verify", "{\"twoFactorToken\":\"" + mfa + "\",\"code\":\"" + Totp.code(key, step, 6) + "\"}", null)
                .andExpect(status().isUnauthorized());
        postJson("/api/v1/auth/2fa/verify", "{\"twoFactorToken\":\"" + mfa + "\",\"code\":\"" + Totp.code(key, step + 1, 6) + "\"}", null)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.user.twoFactorEnabled").value(true))
                .andExpect(jsonPath("$.accessToken").isNotEmpty());
        postJson("/api/v1/auth/2fa/verify", "{\"twoFactorToken\":\"" + access + "\",\"code\":\"123456\"}", null)
                .andExpect(status().isUnauthorized());
    }

    @Test
    void corsAllowsOnlyTheWebApp() throws Exception {
        mvc.perform(options("/api/v1/me").header("Origin", "http://127.0.0.1:8765").header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://127.0.0.1:8765"));
        mvc.perform(options("/api/v1/me").header("Origin", "https://evil.example").header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isForbidden());
        mvc.perform(get("/actuator/health")).andExpect(status().isOk());
        mvc.perform(get("/actuator/env")).andExpect(status().isUnauthorized());
    }
}
