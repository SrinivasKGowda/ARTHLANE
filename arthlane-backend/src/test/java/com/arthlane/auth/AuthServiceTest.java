package com.arthlane.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

import com.arthlane.common.ApiException;

class AuthServiceTest {

    @Test
    void normalizesIndianMobilesAndEmails() {
        assertThat(AuthService.normalize("98765 43210")).isEqualTo("+919876543210");
        assertThat(AuthService.normalize("+91-98765-43210")).isEqualTo("+919876543210");
        assertThat(AuthService.normalize("919876543210")).isEqualTo("+919876543210");
        assertThat(AuthService.normalize("09876543210")).isEqualTo("+919876543210");
        assertThat(AuthService.normalize("  Srini@Example.IN ")).isEqualTo("srini@example.in");
    }

    @Test
    void rejectsBadDestinations() {
        assertThatThrownBy(() -> AuthService.normalize("12345")).isInstanceOf(ApiException.class);
        assertThatThrownBy(() -> AuthService.normalize("5876543210")).isInstanceOf(ApiException.class);
        assertThatThrownBy(() -> AuthService.normalize("not@mail")).isInstanceOf(ApiException.class);
        assertThatThrownBy(() -> AuthService.normalize(null)).isInstanceOf(ApiException.class);
    }
}
