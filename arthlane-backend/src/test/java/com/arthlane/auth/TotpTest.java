package com.arthlane.auth;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;

import org.junit.jupiter.api.Test;

class TotpTest {

    private static final byte[] RFC_KEY = "12345678901234567890".getBytes(StandardCharsets.US_ASCII);

    @Test
    void matchesRfc6238Sha1Vectors() {
        assertThat(Totp.code(RFC_KEY, 59L / 30, 8)).isEqualTo("94287082");
        assertThat(Totp.code(RFC_KEY, 1111111109L / 30, 8)).isEqualTo("07081804");
        assertThat(Totp.code(RFC_KEY, 1111111111L / 30, 8)).isEqualTo("14050471");
        assertThat(Totp.code(RFC_KEY, 1234567890L / 30, 8)).isEqualTo("89005924");
        assertThat(Totp.code(RFC_KEY, 2000000000L / 30, 8)).isEqualTo("69279037");
        assertThat(Totp.code(RFC_KEY, 20000000000L / 30, 8)).isEqualTo("65353130");
    }

    @Test
    void base32RoundTrips() {
        String secret = Totp.base32Encode(RFC_KEY);
        assertThat(secret).isEqualTo("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ");
        assertThat(Totp.base32Decode(secret)).isEqualTo(RFC_KEY);
    }

    @Test
    void acceptsOneStepOfDriftOnly() {
        String secret = Totp.base32Encode(RFC_KEY);
        long now = 1_700_000_000L;
        long step = now / 30;
        assertThat(Totp.verify(secret, Totp.code(RFC_KEY, step, 6), now)).isEqualTo(step);
        assertThat(Totp.verify(secret, Totp.code(RFC_KEY, step - 1, 6), now)).isEqualTo(step - 1);
        assertThat(Totp.verify(secret, Totp.code(RFC_KEY, step + 1, 6), now)).isEqualTo(step + 1);
        assertThat(Totp.verify(secret, Totp.code(RFC_KEY, step + 2, 6), now)).isEqualTo(-1);
        assertThat(Totp.verify(secret, "12ab56", now)).isEqualTo(-1);
    }

    @Test
    void buildsAnAuthenticatorUri() {
        assertThat(Totp.otpauthUri("Arthlane", "a@b.in", "ABC"))
                .isEqualTo("otpauth://totp/Arthlane%3Aa%40b.in?secret=ABC&issuer=Arthlane&algorithm=SHA1&digits=6&period=30");
    }
}
