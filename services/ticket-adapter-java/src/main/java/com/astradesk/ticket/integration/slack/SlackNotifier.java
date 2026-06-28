// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/integration/slack/SlackNotifier.java
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/ticket-adapter-java/src/main/java/com/astradesk/ticket/integration/slack/SlackNotifier.java.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

package com.astradesk.ticket.integration.slack;

import java.util.Map;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.reactive.function.client.WebClient;

import com.astradesk.ticket.domain.Ticket;
import com.astradesk.ticket.integration.props.IntegrationProperties;

import reactor.core.publisher.Mono;

/**
 * Sends structured messages to Slack via an Incoming Webhook. The payload format is
 * intentionally simple (single block of text) so the adapter can operate even when
 * Slack is configured with the most basic webhook tier.
 */
@Component
public class SlackNotifier {

    private static final Logger log = LoggerFactory.getLogger(SlackNotifier.class);

    private final IntegrationProperties.SlackProperties properties;
    private final IntegrationProperties.FrontendProperties frontendProperties;
    private final WebClient webClient;

    public SlackNotifier(WebClient.Builder builder, IntegrationProperties integrationProperties) {
        this.properties = integrationProperties.getSlack();
        this.frontendProperties = integrationProperties.getFrontend();
        this.webClient = builder.build();
    }

    public Mono<Void> notifyTicketCreated(Ticket ticket) {
        if (!properties.isEnabled()) {
            log.debug("Slack notifications disabled; skipping create message for ticket {}", ticket.getId());
            return Mono.empty();
        }

        String text = """
            :ticket: *New ticket* <%s|#%d – %s>
            Status: `%s`
            Jira: %s
            """.formatted(
                ticketUrl(ticket),
                ticket.getId(),
                ticket.getTitle(),
                ticket.getStatus(),
                Optional.ofNullable(ticket.getJiraIssueKey()).orElse("not created")
            );

        return sendMessage(text, ticket.getSlackChannel());
    }

    public Mono<Void> notifyTicketStatusChange(Ticket ticket) {
        if (!properties.isEnabled()) {
            log.debug("Slack notifications disabled; skipping status message for ticket {}", ticket.getId());
            return Mono.empty();
        }

        String text = """
            :information_source: *Ticket #%d* is now `%s`.
            <%s|Open in AstraDesk>.
            """.formatted(
                ticket.getId(),
                ticket.getStatus(),
                ticketUrl(ticket)
            );

        return sendMessage(text, ticket.getSlackChannel());
    }

    private Mono<Void> sendMessage(String text, String ticketChannel) {
        String channel = resolveChannel(ticketChannel);
        Map<String, Object> payload = channel == null
            ? Map.of("text", text)
            : Map.of("text", text, "channel", channel);

        return webClient.post()
            .uri(properties.getWebhookUrl())
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(payload)
            .retrieve()
            .bodyToMono(String.class)
            .doOnNext(response -> log.debug("Slack webhook responded with: {}", response))
            .then();
    }

    private String resolveChannel(String ticketChannel) {
        if (StringUtils.hasText(ticketChannel)) {
            return ticketChannel;
        }
        return StringUtils.hasText(properties.getDefaultChannel())
            ? properties.getDefaultChannel()
            : null;
    }

    private String ticketUrl(Ticket ticket) {
        return "%s/tickets/%d".formatted(frontendProperties.getBaseUrl(), ticket.getId());
    }
}
