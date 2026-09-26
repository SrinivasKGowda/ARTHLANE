package com.arthlane.auth;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/** Development only: codes in logs would let anyone with log access sign in as anyone. */
@Component
@Order(100)
@ConditionalOnProperty(name = "arthlane.otp.dev-echo", havingValue = "true")
public class LoggingOtpSender implements OtpSender {

    private static final Logger log = LoggerFactory.getLogger(LoggingOtpSender.class);

    @Override
    public boolean supports(String destination) {
        return true;
    }

    @Override
    public void send(String destination, String code) {
        log.info("Sign-in code for {} is {} (development sender: connect an SMS or email provider for real delivery)", destination, code);
    }
}
