package com.arthlane.paper;

import java.math.BigDecimal;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

public final class PaperDtos {

    private PaperDtos() {
    }

    public record PositionDto(Long id, String clientRef, String kind, String symbol, String label, String side,
            BigDecimal qty, BigDecimal entry, BigDecimal stop, BigDecimal target, String optionType, BigDecimal strike,
            String expiry, Integer lots, Integer lotSize, long openedAt) {

        static PositionDto from(Position p) {
            return new PositionDto(p.getId(), p.getClientRef(), p.getKind(), p.getSymbol(), p.getLabel(), p.getSide(),
                    p.getQty(), p.getEntry(), p.getStop(), p.getTarget(), p.getOptionType(), p.getStrike(), p.getExpiry(),
                    p.getLots(), p.getLotSize(), p.getOpenedAt().toEpochMilli());
        }
    }

    /** The web app prices the exit from live data; the server does the profit and loss arithmetic. */
    public record CloseRequest(
            @NotNull @DecimalMin("0") BigDecimal exitPrice,
            @DecimalMin(value = "0", inclusive = false) @DecimalMax("1000") BigDecimal fxRate,
            @Size(max = 40) String clientRef) {
    }

    public record JournalDto(Long id, String clientRef, String symbol, String label, String side, BigDecimal units,
            BigDecimal entry, BigDecimal exit, BigDecimal pnl, long openedAt, long closedAt) {

        static JournalDto from(JournalEntry j) {
            return new JournalDto(j.getId(), j.getClientRef(), j.getSymbol(), j.getLabel(), j.getSide(), j.getUnits(),
                    j.getEntry(), j.getExitPrice(), j.getPnl(), j.getOpenedAt().toEpochMilli(), j.getClosedAt().toEpochMilli());
        }
    }

    /** Used to bring trades recorded before sign-in into the account. */
    public record NewJournalEntry(
            @Size(max = 40) String clientRef,
            @NotBlank @Size(max = 40) String symbol,
            @NotBlank @Size(max = 80) String label,
            @NotNull @Pattern(regexp = "[BS]") String side,
            @NotNull @Positive BigDecimal units,
            @NotNull @DecimalMin("0") BigDecimal entry,
            @NotNull @DecimalMin("0") BigDecimal exit,
            @NotNull BigDecimal pnl,
            @NotNull Long openedAt,
            @NotNull Long closedAt) {
    }

    public record JournalStats(int trades, int wins, int losses, Double winRate, BigDecimal totalPnl, BigDecimal avgWin,
            BigDecimal avgLoss, BigDecimal best, BigDecimal worst, Double profitFactor) {
    }
}
