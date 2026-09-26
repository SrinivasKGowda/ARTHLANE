package com.arthlane.paper;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.arthlane.common.ApiException;
import com.arthlane.paper.PaperDtos.CloseRequest;
import com.arthlane.paper.PaperDtos.JournalDto;
import com.arthlane.paper.PaperDtos.JournalStats;
import com.arthlane.paper.PaperDtos.NewJournalEntry;
import com.arthlane.paper.PaperDtos.PositionDto;

@Service
public class PaperService {

    static final int MAX_OPEN_POSITIONS = 200;
    static final int MAX_JOURNAL_ENTRIES = 5000;

    private final PositionRepository positions;
    private final JournalRepository journal;

    public PaperService(PositionRepository positions, JournalRepository journal) {
        this.positions = positions;
        this.journal = journal;
    }

    @Transactional(readOnly = true)
    public List<PositionDto> positions(Long userId) {
        return positions.findByUserIdOrderByOpenedAtAsc(userId).stream().map(PositionDto::from).toList();
    }

    /** Sending the same clientRef twice returns the first position, so retries and first-sign-in uploads are safe. */
    @Transactional
    public PositionDto open(Long userId, NewPosition body) {
        if (!body.complete()) {
            throw ApiException.badRequest("A stock position needs a symbol and quantity; an option needs a type, strike, expiry, lots and lot size");
        }
        if (body.clientRef() != null) {
            var existing = positions.findByUserIdAndClientRef(userId, body.clientRef());
            if (existing.isPresent()) {
                return PositionDto.from(existing.get());
            }
        }
        if (positions.countByUserId(userId) >= MAX_OPEN_POSITIONS) {
            throw ApiException.badRequest("You can hold up to " + MAX_OPEN_POSITIONS + " open paper positions. Close some first.");
        }
        Instant opened = body.openedAt() == null ? Instant.now() : Instant.ofEpochMilli(body.openedAt());
        return PositionDto.from(positions.save(new Position(userId, body, opened)));
    }

    @Transactional
    public JournalDto close(Long userId, Long id, CloseRequest body) {
        if (body.clientRef() != null) {
            var recorded = journal.findByUserIdAndClientRef(userId, body.clientRef());
            if (recorded.isPresent()) {
                positions.findByIdAndUserId(id, userId).ifPresent(positions::delete);
                return JournalDto.from(recorded.get());
            }
        }
        Position p = positions.findByIdAndUserId(id, userId)
                .orElseThrow(() -> ApiException.notFound("That position is already closed"));
        BigDecimal units = p.units();
        BigDecimal direction = "B".equals(p.getSide()) ? BigDecimal.ONE : BigDecimal.ONE.negate();
        BigDecimal fx = body.fxRate() == null ? BigDecimal.ONE : body.fxRate();
        BigDecimal pnl = body.exitPrice().subtract(p.getEntry()).multiply(direction).multiply(units).multiply(fx)
                .setScale(2, RoundingMode.HALF_UP);
        JournalEntry entry = journal.save(new JournalEntry(userId, p.getSymbol(), p.getLabel(), p.getSide(), units,
                p.getEntry(), body.exitPrice(), pnl, p.getOpenedAt(), Instant.now(), body.clientRef()));
        positions.delete(p);
        return JournalDto.from(entry);
    }

    @Transactional
    public void remove(Long userId, Long id) {
        positions.delete(positions.findByIdAndUserId(id, userId)
                .orElseThrow(() -> ApiException.notFound("That position does not exist")));
    }

    @Transactional(readOnly = true)
    public List<JournalDto> journal(Long userId) {
        return journal.findByUserIdOrderByClosedAtDesc(userId).stream().map(JournalDto::from).toList();
    }

    @Transactional
    public JournalDto record(Long userId, NewJournalEntry body) {
        if (body.clientRef() != null) {
            var existing = journal.findByUserIdAndClientRef(userId, body.clientRef());
            if (existing.isPresent()) {
                return JournalDto.from(existing.get());
            }
        }
        if (journal.countByUserId(userId) >= MAX_JOURNAL_ENTRIES) {
            throw ApiException.badRequest("Your journal is full (" + MAX_JOURNAL_ENTRIES + " trades). Delete old entries first.");
        }
        return JournalDto.from(journal.save(new JournalEntry(userId, body.symbol(), body.label(), body.side(), body.units(),
                body.entry(), body.exit(), body.pnl().setScale(2, RoundingMode.HALF_UP),
                Instant.ofEpochMilli(body.openedAt()), Instant.ofEpochMilli(body.closedAt()), body.clientRef())));
    }

    @Transactional
    public void forget(Long userId, Long id) {
        journal.delete(journal.findByIdAndUserId(id, userId)
                .orElseThrow(() -> ApiException.notFound("That journal entry does not exist")));
    }

    /** Win rate and averages count decided trades only; a flat close is neither a win nor a loss. */
    @Transactional(readOnly = true)
    public JournalStats stats(Long userId) {
        List<BigDecimal> pnls = journal.findByUserIdOrderByClosedAtDesc(userId).stream().map(JournalEntry::getPnl).toList();
        List<BigDecimal> wins = pnls.stream().filter(v -> v.signum() > 0).toList();
        List<BigDecimal> losses = pnls.stream().filter(v -> v.signum() < 0).toList();
        BigDecimal won = sum(wins);
        BigDecimal lost = sum(losses).abs();
        int decided = wins.size() + losses.size();
        return new JournalStats(
                pnls.size(),
                wins.size(),
                losses.size(),
                decided == 0 ? null : Math.round(1000.0 * wins.size() / decided) / 10.0,
                sum(pnls),
                average(wins),
                average(losses),
                pnls.stream().max(BigDecimal::compareTo).orElse(null),
                pnls.stream().min(BigDecimal::compareTo).orElse(null),
                lost.signum() == 0 ? null : won.divide(lost, 2, RoundingMode.HALF_UP).doubleValue());
    }

    private static BigDecimal sum(List<BigDecimal> values) {
        return values.stream().reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    private static BigDecimal average(List<BigDecimal> values) {
        return values.isEmpty() ? null : sum(values).divide(BigDecimal.valueOf(values.size()), 2, RoundingMode.HALF_UP);
    }
}
