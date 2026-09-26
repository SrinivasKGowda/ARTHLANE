package com.arthlane.config;

import java.time.Duration;
import java.util.List;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("arthlane")
public record ArthlaneProperties(Jwt jwt, Otp otp, List<String> corsOrigins) {

    public record Jwt(String secret, Duration accessTtl, Duration refreshTtl) {
    }

    /**
     * devEcho returns the code in the API response and prints it to the log, so the app works before an SMS or email
     * provider is connected. It must be off in production.
     */
    public record Otp(Duration ttl, int maxAttempts, Duration resendAfter, int maxPerHour, int maxPerIpPerHour,
            boolean devEcho, String mailFrom) {
    }
}
