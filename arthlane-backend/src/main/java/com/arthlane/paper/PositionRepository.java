package com.arthlane.paper;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

public interface PositionRepository extends JpaRepository<Position, Long> {

    List<Position> findByUserIdOrderByOpenedAtAsc(Long userId);

    Optional<Position> findByIdAndUserId(Long id, Long userId);

    Optional<Position> findByUserIdAndClientRef(Long userId, String clientRef);

    long countByUserId(Long userId);
}
