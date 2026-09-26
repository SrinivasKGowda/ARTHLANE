package com.arthlane.auth;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService auth;
    private final TokenService tokens;

    public AuthController(AuthService auth, TokenService tokens) {
        this.auth = auth;
        this.tokens = tokens;
    }

    public record OtpRequest(@NotBlank @Size(max = 254) String destination) {
    }

    public record OtpVerify(@NotBlank @Size(max = 254) String destination, @NotBlank @Size(max = 10) String code) {
    }

    public record TwoFactorVerify(@NotBlank String twoFactorToken, @NotBlank @Size(max = 10) String code) {
    }

    public record RefreshRequest(@NotBlank String refreshToken) {
    }

    @PostMapping("/otp/request")
    public AuthService.OtpSent requestOtp(@Valid @RequestBody OtpRequest body, HttpServletRequest request) {
        return auth.requestOtp(body.destination(), request.getRemoteAddr());
    }

    @PostMapping("/otp/verify")
    public AuthService.SignIn verifyOtp(@Valid @RequestBody OtpVerify body) {
        return auth.verifyOtp(body.destination(), body.code());
    }

    @PostMapping("/2fa/verify")
    public AuthService.SignIn verifyTwoFactor(@Valid @RequestBody TwoFactorVerify body) {
        return auth.verifyTwoFactor(body.twoFactorToken(), body.code());
    }

    @PostMapping("/refresh")
    public TokenService.Tokens refresh(@Valid @RequestBody RefreshRequest body) {
        return tokens.rotate(body.refreshToken());
    }

    @PostMapping("/logout")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void logout(@Valid @RequestBody RefreshRequest body) {
        tokens.revoke(body.refreshToken());
    }
}
