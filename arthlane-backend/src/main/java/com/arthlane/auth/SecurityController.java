package com.arthlane.auth;

import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.arthlane.common.ApiException;
import com.arthlane.common.Hashing;
import com.arthlane.user.ProfileController;
import com.arthlane.user.User;
import com.arthlane.user.UserRepository;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;

@RestController
@RequestMapping("/api/v1/me/security")
public class SecurityController {

    private final UserRepository users;
    private final AuthService auth;
    private final TokenService tokens;

    public SecurityController(UserRepository users, AuthService auth, TokenService tokens) {
        this.users = users;
        this.auth = auth;
        this.tokens = tokens;
    }

    public record CodeRequest(@NotBlank String code) {
    }

    public record TwoFactorSetup(String secret, String otpauthUri) {
    }

    /** Starts two-factor setup. The secret only takes effect once a code from the authenticator app is confirmed. */
    @PostMapping("/2fa/setup")
    @Transactional
    public TwoFactorSetup setup(@AuthenticationPrincipal Jwt jwt) {
        User user = ProfileController.current(users, jwt);
        if (user.isTotpEnabled()) {
            throw ApiException.badRequest("Two-factor sign-in is already on. Turn it off first to move it to a new phone.");
        }
        String secret = Totp.newSecret(Hashing.randomBytes(20));
        user.setTotpSecret(secret);
        user.setTotpLastStep(null);
        String account = user.getEmail() != null ? user.getEmail() : user.getPhone();
        return new TwoFactorSetup(secret, Totp.otpauthUri("Arthlane", account, secret));
    }

    @PostMapping("/2fa/enable")
    @Transactional(noRollbackFor = ApiException.class)
    public Map<String, Boolean> enable(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody CodeRequest body) {
        User user = ProfileController.current(users, jwt);
        if (user.isTotpEnabled()) {
            return Map.of("enabled", true);
        }
        auth.checkTotp(user, body.code());
        user.setTotpEnabled(true);
        return Map.of("enabled", true);
    }

    @PostMapping("/2fa/disable")
    @Transactional(noRollbackFor = ApiException.class)
    public Map<String, Boolean> disable(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody CodeRequest body) {
        User user = ProfileController.current(users, jwt);
        if (!user.isTotpEnabled()) {
            throw ApiException.badRequest("Two-factor sign-in is not on");
        }
        auth.checkTotp(user, body.code());
        user.setTotpEnabled(false);
        user.setTotpSecret(null);
        user.setTotpLastStep(null);
        return Map.of("enabled", false);
    }

    @PostMapping("/logout-all")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void logoutAll(@AuthenticationPrincipal Jwt jwt) {
        tokens.revokeAll(ProfileController.current(users, jwt).getId());
    }
}
