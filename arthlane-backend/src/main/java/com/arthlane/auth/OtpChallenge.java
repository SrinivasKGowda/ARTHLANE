package com.arthlane.auth;

import java.time.Instant;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "otp_challenges")
public class OtpChallenge {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String destination;
    private String codeHash;
    private int attempts;
    private Instant createdAt;
    private Instant expiresAt;
    private Instant usedAt;

    protected OtpChallenge() {
    }

    public OtpChallenge(String destination, String codeHash, Instant createdAt, Instant expiresAt) {
        this.destination = destination;
        this.codeHash = codeHash;
        this.createdAt = createdAt;
        this.expiresAt = expiresAt;
    }

    public boolean isOpen(Instant now) {
        return usedAt == null && now.isBefore(expiresAt);
    }

    public Long getId() { return id; }
    public String getDestination() { return destination; }
    public String getCodeHash() { return codeHash; }
    public int getAttempts() { return attempts; }
    public void addAttempt() { attempts++; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getExpiresAt() { return expiresAt; }
    public Instant getUsedAt() { return usedAt; }
    public void markUsed(Instant when) { usedAt = when; }
}
