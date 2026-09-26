package com.arthlane.paper;

import java.math.BigDecimal;
import java.time.Instant;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "paper_positions")
public class Position {

    public static final String EQUITY = "eq";
    public static final String OPTION = "opt";

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long userId;
    private String kind;
    private String symbol;
    private String label;
    private String side;
    private BigDecimal qty;
    private BigDecimal entry;
    private BigDecimal stop;
    private BigDecimal target;
    private String optionType;
    private BigDecimal strike;
    private String expiry;
    private Integer lots;
    private Integer lotSize;
    private Instant openedAt;
    private String clientRef;

    protected Position() {
    }

    Position(Long userId, NewPosition p, Instant openedAt) {
        this.userId = userId;
        this.kind = p.kind();
        this.symbol = OPTION.equals(p.kind()) && p.symbol() == null ? "^NSEI" : p.symbol();
        this.label = p.label();
        this.side = p.side();
        this.entry = p.entry();
        this.openedAt = openedAt;
        this.clientRef = p.clientRef();
        if (EQUITY.equals(p.kind())) {
            this.qty = p.qty();
            this.stop = p.stop();
            this.target = p.target();
        } else {
            this.optionType = p.optionType();
            this.strike = p.strike();
            this.expiry = p.expiry();
            this.lots = p.lots();
            this.lotSize = p.lotSize();
        }
    }

    /** Shares or coins for equity-style positions; contracts times lot size for options. */
    public BigDecimal units() {
        return EQUITY.equals(kind) ? qty : BigDecimal.valueOf((long) lots * lotSize);
    }

    public Long getId() { return id; }
    public Long getUserId() { return userId; }
    public String getKind() { return kind; }
    public String getSymbol() { return symbol; }
    public String getLabel() { return label; }
    public String getSide() { return side; }
    public BigDecimal getQty() { return qty; }
    public BigDecimal getEntry() { return entry; }
    public BigDecimal getStop() { return stop; }
    public BigDecimal getTarget() { return target; }
    public String getOptionType() { return optionType; }
    public BigDecimal getStrike() { return strike; }
    public String getExpiry() { return expiry; }
    public Integer getLots() { return lots; }
    public Integer getLotSize() { return lotSize; }
    public Instant getOpenedAt() { return openedAt; }
    public String getClientRef() { return clientRef; }
}
