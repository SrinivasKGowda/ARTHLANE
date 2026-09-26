package com.arthlane.paper;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.arthlane.paper.PaperDtos.CloseRequest;
import com.arthlane.paper.PaperDtos.JournalDto;
import com.arthlane.paper.PaperDtos.JournalStats;
import com.arthlane.paper.PaperDtos.NewJournalEntry;
import com.arthlane.paper.PaperDtos.PositionDto;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/v1")
public class PaperController {

    private final PaperService paper;

    public PaperController(PaperService paper) {
        this.paper = paper;
    }

    private static Long user(Jwt jwt) {
        return Long.valueOf(jwt.getSubject());
    }

    @GetMapping("/positions")
    public List<PositionDto> positions(@AuthenticationPrincipal Jwt jwt) {
        return paper.positions(user(jwt));
    }

    @PostMapping("/positions")
    public PositionDto open(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody NewPosition body) {
        return paper.open(user(jwt), body);
    }

    @PostMapping("/positions/{id}/close")
    public JournalDto close(@AuthenticationPrincipal Jwt jwt, @PathVariable Long id, @Valid @RequestBody CloseRequest body) {
        return paper.close(user(jwt), id, body);
    }

    @DeleteMapping("/positions/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void remove(@AuthenticationPrincipal Jwt jwt, @PathVariable Long id) {
        paper.remove(user(jwt), id);
    }

    @GetMapping("/journal")
    public List<JournalDto> journal(@AuthenticationPrincipal Jwt jwt) {
        return paper.journal(user(jwt));
    }

    @PostMapping("/journal")
    public JournalDto record(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody NewJournalEntry body) {
        return paper.record(user(jwt), body);
    }

    @DeleteMapping("/journal/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void forget(@AuthenticationPrincipal Jwt jwt, @PathVariable Long id) {
        paper.forget(user(jwt), id);
    }

    @GetMapping("/journal/stats")
    public JournalStats stats(@AuthenticationPrincipal Jwt jwt) {
        return paper.stats(user(jwt));
    }
}
