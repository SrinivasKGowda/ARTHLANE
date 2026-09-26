package com.arthlane.paper;

import java.math.BigDecimal;
import java.time.Instant;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "journal_entries")
public class JournalEntry {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long userId;
    private String symbol;
    private String label;
    private String side;
    private BigDecimal units;
    private BigDecimal entry;
    private BigDecimal exitPrice;
    private BigDecimal pnl;
    private Instant openedAt;
    private Instant closedAt;
    private String clientRef;

    protected JournalEntry() {
    }

    JournalEntry(Long userId, String symbol, String label, String side, BigDecimal units, BigDecimal entry,
            BigDecimal exitPrice, BigDecimal pnl, Instant openedAt, Instant closedAt, String clientRef) {
        this.userId = userId;
        this.symbol = symbol;
        this.label = label;
        this.side = side;
        this.units = units;
        this.entry = entry;
        this.exitPrice = exitPrice;
        this.pnl = pnl;
        this.openedAt = openedAt;
        this.closedAt = closedAt;
        this.clientRef = clientRef;
    }

    public Long getId() { return id; }
    public Long getUserId() { return userId; }
    public String getSymbol() { return symbol; }
    public String getLabel() { return label; }
    public String getSide() { return side; }
    public BigDecimal getUnits() { return units; }
    public BigDecimal getEntry() { return entry; }
    public BigDecimal getExitPrice() { return exitPrice; }
    public BigDecimal getPnl() { return pnl; }
    public Instant getOpenedAt() { return openedAt; }
    public Instant getClosedAt() { return closedAt; }
    public String getClientRef() { return clientRef; }
}
