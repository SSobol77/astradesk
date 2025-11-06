package com.astradesk.ticket.service;

import java.time.Clock;
import java.time.Instant;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.astradesk.ticket.domain.Ticket;
import com.astradesk.ticket.repository.TicketRepository;
import com.astradesk.ticket.web.dto.TicketRequest;
import com.astradesk.ticket.web.dto.TicketUpdateRequest;
import com.astradesk.ticket.integration.jira.JiraClient;
import com.astradesk.ticket.integration.jira.JiraIssue;
import com.astradesk.ticket.integration.slack.SlackNotifier;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Application service orchestrating persistence and outbound integrations.
 *
 * <p>Responsibilities:
 * <ul>
 *   <li>Persist tickets via {@link TicketRepository}</li>
 *   <li>Open Jira issues to keep the service desk in sync</li>
 *   <li>Push Slack notifications to keep the on-call team informed</li>
 * </ul>
 * The service is reactive end-to-end to avoid blocking Netty threads.</p>
 */
@Service
public class TicketService {

    private static final Logger log = LoggerFactory.getLogger(TicketService.class);

    private final TicketRepository ticketRepository;
    private final JiraClient jiraClient;
    private final SlackNotifier slackNotifier;
    private final Clock clock;

    public TicketService(
        TicketRepository ticketRepository,
        JiraClient jiraClient,
        SlackNotifier slackNotifier,
        Clock clock
    ) {
        this.ticketRepository = ticketRepository;
        this.jiraClient = jiraClient;
        this.slackNotifier = slackNotifier;
        this.clock = clock;
    }

    /**
     * Creates a ticket, mirrors it to Jira and sends a Slack heads-up. Failures in
     * outbound systems do not abort the main persistence flow – instead we log and
     * continue, so the frontend still gets a ticket id to work with.
     */
    @Transactional
    public Mono<Ticket> createTicket(TicketRequest request) {
        Instant now = clock.instant();
        Ticket ticket = Ticket.newTicket(request.getTitle(), request.getBody());
        ticket.setSlackChannel(request.getSlackChannel());
        ticket.setCreatedAt(now);
        ticket.setUpdatedAt(now);

        Mono<JiraIssue> jiraIssueMono = jiraClient.createIssue(ticket, request.getPriority())
            .doOnNext(issue -> ticket.setJiraIssueKey(issue.key()))
            .doOnError(error -> log.warn("Failed to create Jira issue for ticket '{}': {}", ticket.getTitle(), error.getMessage()))
            .onErrorResume(error -> Mono.empty());

        Mono<Ticket> savedTicket = jiraIssueMono
            .then(ticketRepository.save(ticket));

        return savedTicket.flatMap(saved ->
            slackNotifier.notifyTicketCreated(saved)
                .doOnError(error -> log.warn("Failed to send Slack notification for ticket {}: {}", saved.getId(), error.getMessage()))
                .onErrorResume(error -> Mono.empty())
                .thenReturn(saved)
        );
    }

    public Mono<Ticket> getTicket(Long id) {
        return ticketRepository.findById(id)
            .switchIfEmpty(Mono.error(new TicketNotFoundException(id)));
    }

    public Flux<Ticket> listTickets() {
        return ticketRepository.findAll();
    }

    /**
     * Updates ticket status and optional metadata. Slack receives a status update
     * notification only when the status actually changes.
     */
    @Transactional
    public Mono<Ticket> updateTicket(Long id, TicketUpdateRequest request) {
        return ticketRepository.findById(id)
            .switchIfEmpty(Mono.error(new TicketNotFoundException(id)))
            .flatMap(ticket -> {
                boolean statusChanged = request.getStatus() != null && request.getStatus() != ticket.getStatus();
                if (request.getStatus() != null) {
                    ticket.setStatus(request.getStatus());
                }
                if (request.getSlackChannel() != null) {
                    ticket.setSlackChannel(request.getSlackChannel());
                }
                ticket.setUpdatedAt(clock.instant());

                Mono<Ticket> saved = ticketRepository.save(ticket);
                if (!statusChanged) {
                    return saved;
                }

                return saved.flatMap(updated ->
                    slackNotifier.notifyTicketStatusChange(updated)
                        .doOnError(error -> log.warn("Failed to send Slack status notification for ticket {}: {}", updated.getId(), error.getMessage()))
                        .onErrorResume(error -> Mono.empty())
                        .thenReturn(updated)
                );
            });
    }
}
