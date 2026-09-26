package com.arthlane.auth;

import java.time.Instant;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

public interface OtpChallengeRepository extends JpaRepository<OtpChallenge, Long> {

    Optional<OtpChallenge> findFirstByDestinationOrderByCreatedAtDesc(String destination);

    long countByDestinationAndCreatedAtAfter(String destination, Instant since);
}
