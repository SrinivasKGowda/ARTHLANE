package com.arthlane.auth;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.arthlane.common.ApiException;
import com.arthlane.common.Hashing;
import com.arthlane.config.ArthlaneProperties;
import com.arthlane.user.ProfileDto;
import com.arthlane.user.User;
import com.arthlane.user.UserRepository;

@Service
public class AuthService {

    private static final Pattern EMAIL = Pattern.compile("^[^@\\s]{1,64}@[^@\\s]+\\.[^@\\s]{2,}$");
    private static final Pattern MOBILE = Pattern.compile("[6-9]\\d{9}");

    private static final Logger log = LoggerFactory.getLogger(AuthService.class);

    private final OtpChallengeRepository challenges;
    private final UserRepository users;
    private final List<OtpSender> senders;
    private final TokenService tokens;
    private final AttemptLimiter limiter;
    private final ArthlaneProperties.Otp otp;
    private final byte[] otpKey;

    public AuthService(OtpChallengeRepository challenges, UserRepository users, ObjectProvider<OtpSender> senders,
            TokenService tokens, AttemptLimiter limiter, ArthlaneProperties props) {
        this.challenges = challenges;
        this.users = users;
        this.senders = senders.orderedStream().toList();
        this.tokens = tokens;
        this.limiter = limiter;
        this.otp = props.otp();
        this.otpKey = (props.jwt().secret() + "|otp").getBytes(StandardCharsets.UTF_8);
    }

    public record OtpSent(String destination, long expiresIn, String devCode) {
    }

    public record SignIn(boolean twoFactorRequired, String twoFactorToken, String accessToken, String refreshToken,
            Long expiresIn, ProfileDto user, boolean newUser) {

        static SignIn twoFactor(String token) {
            return new SignIn(true, token, null, null, null, null, false);
        }

        static SignIn done(TokenService.Tokens t, ProfileDto user, boolean newUser) {
            return new SignIn(false, null, t.accessToken(), t.refreshToken(), t.expiresIn(), user, newUser);
        }
    }

    /** Emails are lower-cased; Indian mobiles become +91 followed by ten digits. */
    public static String normalize(String raw) {
        String value = raw == null ? "" : raw.strip();
        if (value.contains("@")) {
            value = value.toLowerCase(Locale.ROOT);
            if (value.length() > 254 || !EMAIL.matcher(value).matches()) {
                throw ApiException.badRequest("Enter a valid email address");
            }
            return value;
        }
        String digits = value.replaceAll("[\\s()-]", "");
        if (digits.startsWith("+91")) {
            digits = digits.substring(3);
        } else if (digits.length() == 12 && digits.startsWith("91")) {
            digits = digits.substring(2);
        } else if (digits.length() == 11 && digits.startsWith("0")) {
            digits = digits.substring(1);
        }
        if (!MOBILE.matcher(digits).matches()) {
            throw ApiException.badRequest("Enter a valid email or a 10-digit Indian mobile number");
        }
        return "+91" + digits;
    }

    @Transactional
    public OtpSent requestOtp(String raw, String address) {
        if (!limiter.allowCodeRequest(address)) {
            throw ApiException.tooMany("Too many sign-in codes were requested from your network. Try again in an hour.");
        }
        String destination = normalize(raw);
        OtpSender sender = senders.stream().filter(s -> s.supports(destination)).findFirst().orElseThrow(() -> destination.contains("@")
                ? new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Sign-in codes cannot be sent right now. Try again later.")
                : ApiException.badRequest("Sign-in with a mobile number is not available yet. Use your email address."));
        Instant now = Instant.now();
        challenges.findFirstByDestinationOrderByCreatedAtDesc(destination).ifPresent(last -> {
            long wait = Duration.between(now, last.getCreatedAt().plus(otp.resendAfter())).toSeconds();
            if (wait > 0) {
                throw ApiException.tooMany("Please wait " + wait + " seconds before asking for another code");
            }
        });
        if (challenges.countByDestinationAndCreatedAtAfter(destination, now.minus(Duration.ofHours(1))) >= otp.maxPerHour()) {
            throw ApiException.tooMany("Too many codes were requested for this address. Try again in an hour.");
        }
        String code = Hashing.randomDigits(6);
        challenges.save(new OtpChallenge(destination, hash(destination, code), now, now.plus(otp.ttl())));
        try {
            sender.send(destination, code);
        } catch (RuntimeException e) {
            log.warn("Could not deliver a sign-in code to {}: {}", destination, e.toString());
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "We could not send your code just now. Try again in a minute.");
        }
        return new OtpSent(destination, otp.ttl().toSeconds(), otp.devEcho() ? code : null);
    }

    @Transactional(noRollbackFor = ApiException.class)
    public SignIn verifyOtp(String raw, String code) {
        String destination = normalize(raw);
        Instant now = Instant.now();
        OtpChallenge challenge = challenges.findFirstByDestinationOrderByCreatedAtDesc(destination)
                .filter(c -> c.isOpen(now))
                .orElseThrow(() -> ApiException.badRequest("This code has expired. Ask for a new one."));
        if (challenge.getAttempts() >= otp.maxAttempts()) {
            throw ApiException.tooMany("Too many wrong codes. Ask for a new one.");
        }
        if (code == null || !Hashing.equalsConstantTime(challenge.getCodeHash(), hash(destination, code.strip()))) {
            challenge.addAttempt();
            int left = otp.maxAttempts() - challenge.getAttempts();
            throw ApiException.unauthorized(left > 0
                    ? "Wrong code. " + left + (left == 1 ? " attempt" : " attempts") + " left."
                    : "Too many wrong codes. Ask for a new one.");
        }
        challenge.markUsed(now);
        boolean email = destination.contains("@");
        User existing = (email ? users.findByEmail(destination) : users.findByPhone(destination)).orElse(null);
        User user = existing != null ? existing : users.save(new User(email ? destination : null, email ? null : destination));
        if (user.isTotpEnabled()) {
            return SignIn.twoFactor(tokens.mfaToken(user.getId()));
        }
        return SignIn.done(tokens.issue(user.getId()), ProfileDto.from(user), existing == null);
    }

    @Transactional(noRollbackFor = ApiException.class)
    public SignIn verifyTwoFactor(String mfaToken, String code) {
        User user = users.findById(tokens.mfaUser(mfaToken))
                .orElseThrow(() -> ApiException.unauthorized("This account no longer exists"));
        checkTotp(user, code);
        return SignIn.done(tokens.issue(user.getId()), ProfileDto.from(user), false);
    }

    /** Accepts each authenticator code once, and locks out after repeated wrong codes. */
    public void checkTotp(User user, String code) {
        if (user.getTotpSecret() == null) {
            throw ApiException.badRequest("Two-factor sign-in is not set up for this account");
        }
        if (limiter.blocked(user.getId())) {
            throw ApiException.tooMany("Too many wrong authenticator codes. Wait five minutes and try again.");
        }
        long step = Totp.verify(user.getTotpSecret(), code, Instant.now().getEpochSecond());
        if (step < 0 || (user.getTotpLastStep() != null && step <= user.getTotpLastStep())) {
            limiter.failed(user.getId());
            throw ApiException.unauthorized("That authenticator code is not valid. Check your phone's clock and use the newest code.");
        }
        limiter.succeeded(user.getId());
        user.setTotpLastStep(step);
    }

    private String hash(String destination, String code) {
        return Hashing.hmacSha256(otpKey, destination + ":" + code);
    }
}
