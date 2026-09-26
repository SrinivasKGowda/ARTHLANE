package com.arthlane.user;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.Arrays;
import java.util.List;

public record ProfileDto(
        Long id,
        String email,
        String phone,
        String name,
        String city,
        String experience,
        String style,
        String risk,
        BigDecimal capital,
        BigDecimal riskPct,
        BigDecimal dailyLoss,
        List<String> segments,
        String startView,
        String boardCity,
        String newsMode,
        String avatar,
        boolean twoFactorEnabled,
        Instant since) {

    public static ProfileDto from(User u) {
        List<String> segments = u.getSegments() == null || u.getSegments().isBlank()
                ? List.of()
                : Arrays.asList(u.getSegments().split(","));
        return new ProfileDto(u.getId(), u.getEmail(), u.getPhone(), u.getName(), u.getCity(), u.getExperience(),
                u.getTradingStyle(), u.getRiskAppetite(), u.getCapital(), u.getRiskPct(), u.getDailyLossPct(), segments,
                u.getStartView(), u.getBoardCity(), u.getNewsMode(), u.getAvatar(), u.isTotpEnabled(), u.getCreatedAt());
    }
}
