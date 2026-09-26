package com.arthlane.auth;

/** Delivers a sign-in code. The first sender that supports a destination is used. */
public interface OtpSender {

    boolean supports(String destination);

    void send(String destination, String code);
}
