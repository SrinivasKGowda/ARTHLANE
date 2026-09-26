package com.arthlane.auth;

import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.core.annotation.Order;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Component;

import com.arthlane.config.ArthlaneProperties;

@Component
@Order(10)
@ConditionalOnExpression("'${spring.mail.host:}' != ''")
public class EmailOtpSender implements OtpSender {

    private final JavaMailSender mail;
    private final ArthlaneProperties.Otp otp;

    public EmailOtpSender(JavaMailSender mail, ArthlaneProperties props) {
        this.mail = mail;
        this.otp = props.otp();
    }

    @Override
    public boolean supports(String destination) {
        return destination.contains("@");
    }

    @Override
    public void send(String destination, String code) {
        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom(otp.mailFrom());
        message.setTo(destination);
        message.setSubject("Your Arthlane sign-in code");
        message.setText("Your Arthlane sign-in code is " + code + ".\n\n"
                + "It works for " + otp.ttl().toMinutes() + " minutes. If you did not try to sign in, ignore this email: "
                + "nobody can get into your account without the code.\n\nArthlane");
        mail.send(message);
    }
}
