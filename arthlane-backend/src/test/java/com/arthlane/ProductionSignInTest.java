package com.arthlane;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import com.arthlane.auth.OtpSender;

/** Sign-in with the development shortcuts off: codes are only delivered, never shown or logged. */
@SpringBootTest(properties = { "arthlane.otp.dev-echo=false", "arthlane.otp.max-per-ip-per-hour=3" })
@AutoConfigureMockMvc
@ActiveProfiles("test")
class ProductionSignInTest {

    static final Map<String, String> INBOX = new HashMap<>();

    @TestConfiguration
    static class Inbox {
        @Bean
        OtpSender inboxSender() {
            return new OtpSender() {
                @Override
                public boolean supports(String destination) {
                    return destination.endsWith("@inbox.test");
                }

                @Override
                public void send(String destination, String code) {
                    INBOX.put(destination, code);
                }
            };
        }
    }

    @Autowired
    MockMvc mvc;

    private ResultActions requestCode(String destination) throws Exception {
        return mvc.perform(post("/api/v1/auth/otp/request").contentType(MediaType.APPLICATION_JSON)
                .content("{\"destination\":\"" + destination + "\"}"));
    }

    @Test
    void deliversCodesWithoutEchoingThemAndLimitsEachNetwork() throws Exception {
        requestCode("9876500001")
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail", containsString("mobile number is not available yet")));
        requestCode("someone@elsewhere.in")
                .andExpect(status().isServiceUnavailable());
        requestCode("trader@inbox.test")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.devCode").value(nullValue()));

        mvc.perform(post("/api/v1/auth/otp/verify").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"destination\":\"trader@inbox.test\",\"code\":\"" + INBOX.get("trader@inbox.test") + "\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.accessToken").isNotEmpty());

        requestCode("other@inbox.test")
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.detail", containsString("your network")));
    }
}
