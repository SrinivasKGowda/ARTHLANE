package com.arthlane.user;

import java.math.BigDecimal;
import java.time.Instant;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;

@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String email;
    private String phone;
    private String name;
    private String city;
    private String experience = "Beginner";
    private String tradingStyle = "Swing";
    private String riskAppetite = "Moderate";
    private BigDecimal capital = new BigDecimal("100000");
    private BigDecimal riskPct = BigDecimal.ONE;
    private BigDecimal dailyLossPct = new BigDecimal("3");
    private String segments = "Equity,F&O";
    private String startView = "terminal";
    private String boardCity;
    private String newsMode;
    private String avatar;
    private String totpSecret;
    private boolean totpEnabled;
    private Long totpLastStep;
    private Instant createdAt;
    private Instant updatedAt;

    protected User() {
    }

    public User(String email, String phone) {
        this.email = email;
        this.phone = phone;
        this.createdAt = Instant.now();
        this.updatedAt = createdAt;
    }

    @PreUpdate
    void touch() {
        updatedAt = Instant.now();
    }

    public Long getId() { return id; }
    public String getEmail() { return email; }
    public String getPhone() { return phone; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getCity() { return city; }
    public void setCity(String city) { this.city = city; }
    public String getExperience() { return experience; }
    public void setExperience(String experience) { this.experience = experience; }
    public String getTradingStyle() { return tradingStyle; }
    public void setTradingStyle(String tradingStyle) { this.tradingStyle = tradingStyle; }
    public String getRiskAppetite() { return riskAppetite; }
    public void setRiskAppetite(String riskAppetite) { this.riskAppetite = riskAppetite; }
    public BigDecimal getCapital() { return capital; }
    public void setCapital(BigDecimal capital) { this.capital = capital; }
    public BigDecimal getRiskPct() { return riskPct; }
    public void setRiskPct(BigDecimal riskPct) { this.riskPct = riskPct; }
    public BigDecimal getDailyLossPct() { return dailyLossPct; }
    public void setDailyLossPct(BigDecimal dailyLossPct) { this.dailyLossPct = dailyLossPct; }
    public String getSegments() { return segments; }
    public void setSegments(String segments) { this.segments = segments; }
    public String getStartView() { return startView; }
    public void setStartView(String startView) { this.startView = startView; }
    public String getBoardCity() { return boardCity; }
    public void setBoardCity(String boardCity) { this.boardCity = boardCity; }
    public String getNewsMode() { return newsMode; }
    public void setNewsMode(String newsMode) { this.newsMode = newsMode; }
    public String getAvatar() { return avatar; }
    public void setAvatar(String avatar) { this.avatar = avatar; }
    public String getTotpSecret() { return totpSecret; }
    public void setTotpSecret(String totpSecret) { this.totpSecret = totpSecret; }
    public boolean isTotpEnabled() { return totpEnabled; }
    public void setTotpEnabled(boolean totpEnabled) { this.totpEnabled = totpEnabled; }
    public Long getTotpLastStep() { return totpLastStep; }
    public void setTotpLastStep(Long totpLastStep) { this.totpLastStep = totpLastStep; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
