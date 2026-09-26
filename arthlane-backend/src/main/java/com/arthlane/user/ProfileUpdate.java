package com.arthlane.user;

import java.math.BigDecimal;
import java.util.List;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/** Email and mobile are not editable here: changing either needs a fresh OTP to the new address. */
public record ProfileUpdate(
        @Size(max = 80) String name,
        @Size(max = 60) String city,
        @Pattern(regexp = "Beginner|Intermediate|Advanced|Professional") String experience,
        @Pattern(regexp = "Intraday|Swing|Positional|Long-term") String style,
        @Pattern(regexp = "Conservative|Moderate|Aggressive") String risk,
        @DecimalMin("0") @DecimalMax("1000000000000") BigDecimal capital,
        @DecimalMin("0") @DecimalMax("100") BigDecimal riskPct,
        @DecimalMin("0") @DecimalMax("100") BigDecimal dailyLoss,
        @Size(max = 10) List<@Pattern(regexp = "Equity|F&O|Commodity|Currency|Crypto") String> segments,
        @Size(max = 20) String startView,
        @Size(max = 60) String boardCity,
        @Pattern(regexp = "sec|min|30m|60m") String newsMode,
        @Size(max = 200000) @Pattern(regexp = "(data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+)?") String avatar) {

    void applyTo(User u) {
        if (name != null) u.setName(name.strip());
        if (city != null) u.setCity(city.strip());
        if (experience != null) u.setExperience(experience);
        if (style != null) u.setTradingStyle(style);
        if (risk != null) u.setRiskAppetite(risk);
        if (capital != null) u.setCapital(capital);
        if (riskPct != null) u.setRiskPct(riskPct);
        if (dailyLoss != null) u.setDailyLossPct(dailyLoss);
        if (segments != null) u.setSegments(String.join(",", segments));
        if (startView != null) u.setStartView(startView);
        if (boardCity != null) u.setBoardCity(boardCity);
        if (newsMode != null) u.setNewsMode(newsMode);
        if (avatar != null) u.setAvatar(avatar.isEmpty() ? null : avatar);
    }
}
