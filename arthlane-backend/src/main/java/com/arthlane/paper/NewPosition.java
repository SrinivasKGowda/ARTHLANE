package com.arthlane.paper;

import java.math.BigDecimal;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

public record NewPosition(
        @Size(max = 40) String clientRef,
        @NotNull @Pattern(regexp = "eq|opt") String kind,
        @Size(max = 40) String symbol,
        @NotBlank @Size(max = 80) String label,
        @NotNull @Pattern(regexp = "[BS]") String side,
        @NotNull @DecimalMin("0") BigDecimal entry,
        @Positive BigDecimal qty,
        @Positive BigDecimal stop,
        @Positive BigDecimal target,
        @Pattern(regexp = "CE|PE") String optionType,
        @Positive BigDecimal strike,
        @Size(max = 20) String expiry,
        @Min(1) @Max(10000) Integer lots,
        @Min(1) @Max(100000) Integer lotSize,
        Long openedAt) {

    boolean complete() {
        if (Position.EQUITY.equals(kind)) {
            return symbol != null && !symbol.isBlank() && qty != null;
        }
        return optionType != null && strike != null && expiry != null && !expiry.isBlank() && lots != null && lotSize != null;
    }
}
