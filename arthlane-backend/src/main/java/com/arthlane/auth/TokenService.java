package com.arthlane.auth;

import java.time.Duration;
import java.time.Instant;

import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.arthlane.common.ApiException;
import com.arthlane.common.Hashing;
import com.arthlane.config.ArthlaneProperties;

@Service
public class TokenService {

    public static final String ISSUER = "arthlane";
    public static final String API_SCOPE = "api";
    static final String MFA_SCOPE = "mfa";
    private static final Duration MFA_TTL = Duration.ofMinutes(5);
    private static final Duration ROTATION_GRACE = Duration.ofSeconds(10);

    private final JwtEncoder encoder;
    private final JwtDecoder decoder;
    private final RefreshTokenRepository refreshTokens;
    private final ArthlaneProperties props;

    public TokenService(JwtEncoder encoder, JwtDecoder decoder, RefreshTokenRepository refreshTokens, ArthlaneProperties props) {
        this.encoder = encoder;
        this.decoder = decoder;
        this.refreshTokens = refreshTokens;
        this.props = props;
    }

    public record Tokens(String accessToken, String refreshToken, long expiresIn) {
    }

    @Transactional
    public Tokens issue(Long userId) {
        Instant now = Instant.now();
        String refresh = Hashing.randomToken();
        refreshTokens.save(new RefreshToken(userId, Hashing.sha256(refresh), now, now.plus(props.jwt().refreshTtl())));
        return new Tokens(jwt(userId, API_SCOPE, props.jwt().accessTtl(), now), refresh, props.jwt().accessTtl().toSeconds());
    }

    /** A short-lived token that only proves the OTP step passed; it cannot call the API. */
    public String mfaToken(Long userId) {
        return jwt(userId, MFA_SCOPE, MFA_TTL, Instant.now());
    }

    public Long mfaUser(String token) {
        try {
            Jwt jwt = decoder.decode(token);
            if (MFA_SCOPE.equals(jwt.getClaimAsString("scope"))) {
                return Long.valueOf(jwt.getSubject());
            }
        } catch (JwtException | IllegalArgumentException e) {
            // fall through to the same answer as a wrong scope
        }
        throw ApiException.unauthorized("Your sign-in step expired. Start again with a new code.");
    }

    /**
     * Refresh tokens are single use. Presenting one that was already swapped means it was copied, so every session of
     * that user ends. Two browser tabs renewing at the same moment is not theft, so a replay within the grace window is
     * only refused. A token that was merely signed out is also just refused.
     */
    @Transactional(noRollbackFor = ApiException.class)
    public Tokens rotate(String refresh) {
        RefreshToken token = refreshTokens.findByTokenHash(Hashing.sha256(refresh == null ? "" : refresh))
                .orElseThrow(() -> ApiException.unauthorized("Your session has ended. Sign in again."));
        Instant now = Instant.now();
        if (token.isRotated()) {
            if (now.isBefore(token.getRevokedAt().plus(ROTATION_GRACE))) {
                throw ApiException.unauthorized("This session was just renewed in another tab.");
            }
            refreshTokens.revokeAll(token.getUserId(), now);
            throw ApiException.unauthorized("This session was already used elsewhere, so all your sessions were signed out. Sign in again.");
        }
        if (token.getRevokedAt() != null || now.isAfter(token.getExpiresAt())) {
            throw ApiException.unauthorized("Your session has ended. Sign in again.");
        }
        token.rotate(now);
        return issue(token.getUserId());
    }

    @Transactional
    public void revoke(String refresh) {
        refreshTokens.findByTokenHash(Hashing.sha256(refresh == null ? "" : refresh)).ifPresent(t -> t.revoke(Instant.now()));
    }

    @Transactional
    public void revokeAll(Long userId) {
        refreshTokens.revokeAll(userId, Instant.now());
    }

    private String jwt(Long userId, String scope, Duration ttl, Instant now) {
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(ISSUER)
                .issuedAt(now)
                .expiresAt(now.plus(ttl))
                .subject(String.valueOf(userId))
                .claim("scope", scope)
                .build();
        return encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(), claims)).getTokenValue();
    }
}
