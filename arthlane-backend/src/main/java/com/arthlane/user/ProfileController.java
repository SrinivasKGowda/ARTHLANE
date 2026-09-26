package com.arthlane.user;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.arthlane.common.ApiException;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/v1/me")
public class ProfileController {

    private final UserRepository users;

    public ProfileController(UserRepository users) {
        this.users = users;
    }

    @GetMapping
    public ProfileDto me(@AuthenticationPrincipal Jwt jwt) {
        return ProfileDto.from(current(users, jwt));
    }

    @PutMapping
    @Transactional
    public ProfileDto update(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody ProfileUpdate update) {
        User user = current(users, jwt);
        update.applyTo(user);
        return ProfileDto.from(users.saveAndFlush(user));
    }

    public static User current(UserRepository users, Jwt jwt) {
        return users.findById(Long.valueOf(jwt.getSubject()))
                .orElseThrow(() -> ApiException.unauthorized("This account no longer exists"));
    }
}
