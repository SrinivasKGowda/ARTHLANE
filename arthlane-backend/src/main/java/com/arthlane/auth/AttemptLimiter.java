package com.arthlane.auth;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.springframework.stereotype.Component;

import com.arthlane.config.ArthlaneProperties;

/** Fixed-window counters kept in memory, so a multi-server deployment should move them to Redis. */
@Component
public class AttemptLimiter {

    private record Window(Instant start, int count) {
    }

    private static final class Counter {

        private final int max;
        private final Duration span;
        private final Map<Object, Window> hits = new ConcurrentHashMap<>();

        Counter(int max, Duration span) {
            this.max = max;
            this.span = span;
        }

        boolean full(Object key) {
            Window w = hits.get(key);
            return w != null && w.count() >= max && Instant.now().isBefore(w.start().plus(span));
        }

        void add(Object key) {
            Instant now = Instant.now();
            if (hits.size() > 50_000) {
                hits.values().removeIf(w -> now.isAfter(w.start().plus(span)));
            }
            hits.compute(key, (k, w) -> w == null || now.isAfter(w.start().plus(span)) ? new Window(now, 1) : new Window(w.start(), w.count() + 1));
        }

        void clear(Object key) {
            hits.remove(key);
        }
    }

    private final Counter totpFailures = new Counter(5, Duration.ofMinutes(5));
    private final Counter codeRequests;

    public AttemptLimiter(ArthlaneProperties props) {
        this.codeRequests = new Counter(props.otp().maxPerIpPerHour(), Duration.ofHours(1));
    }

    public boolean blocked(Long userId) {
        return totpFailures.full(userId);
    }

    public void failed(Long userId) {
        totpFailures.add(userId);
    }

    public void succeeded(Long userId) {
        totpFailures.clear(userId);
    }

    /** Counts a sign-in code request from this network address; false once its hourly allowance is used up. */
    public boolean allowCodeRequest(String address) {
        if (codeRequests.full(address)) {
            return false;
        }
        codeRequests.add(address);
        return true;
    }
}
