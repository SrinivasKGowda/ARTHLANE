package com.arthlane.paper;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

public interface JournalRepository extends JpaRepository<JournalEntry, Long> {

    List<JournalEntry> findByUserIdOrderByClosedAtDesc(Long userId);

    Optional<JournalEntry> findByIdAndUserId(Long id, Long userId);

    Optional<JournalEntry> findByUserIdAndClientRef(Long userId, String clientRef);

    long countByUserId(Long userId);
}
