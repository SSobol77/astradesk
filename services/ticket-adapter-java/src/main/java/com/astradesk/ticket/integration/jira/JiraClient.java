package com.astradesk.ticket.integration.jira;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import com.astradesk.ticket.domain.Ticket;
import com.astradesk.ticket.integration.props.IntegrationProperties;

import reactor.core.publisher.Mono;

/**
 * Minimal Jira REST API client. Only implements the operations required by the
 * adapter – currently issue creation so the service desk stays aligned.
 */
@Component
public class JiraClient {

    private static final Logger log = LoggerFactory.getLogger(JiraClient.class);

    private final WebClient webClient;
    private final IntegrationProperties.JiraProperties properties;

    public JiraClient(WebClient.Builder builder, IntegrationProperties properties) {
        this.properties = properties.getJira();
        if (!this.properties.isEnabled()) {
            this.webClient = null;
        } else {
            this.webClient = builder
                .baseUrl(this.properties.getBaseUrl())
                .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .defaultHeader(HttpHeaders.AUTHORIZATION, basicAuthHeader(this.properties.getUsername(), this.properties.getApiToken()))
                .build();
        }
    }

    /**
     * Creates an issue in Jira. When integration is disabled a completed Mono is
     * returned immediately so the service can operate in "offline" mode.
     */
    public Mono<JiraIssue> createIssue(Ticket ticket, String priority) {
        if (!properties.isEnabled()) {
            log.debug("Jira integration disabled; skipping issue creation for ticket '{}'", ticket.getTitle());
            return Mono.empty();
        }

        Map<String, Object> payload = Map.of(
            "fields", Map.of(
                "project", Map.of("key", properties.getProjectKey()),
                "summary", ticket.getTitle(),
                "description", ticket.getBody(),
                "issuetype", Map.of("name", properties.getIssueType()),
                "priority", priorityPayload(priority)
            )
        );

        return webClient.post()
            .uri("/rest/api/3/issue")
            .bodyValue(payload)
            .retrieve()
            .bodyToMono(JiraIssueResponse.class)
            .map(response -> new JiraIssue(response.id(), response.key(), response.self()))
            .doOnSuccess(issue -> log.info("Created Jira issue {} for ticket {}", issue.key(), ticket.getTitle()));
    }

    private Map<String, Object> priorityPayload(String priority) {
        if (priority == null || priority.isBlank()) {
            return Map.of("name", properties.getDefaultPriority());
        }
        return Map.of("name", priority);
    }

    private String basicAuthHeader(String username, String apiToken) {
        String token = Base64.getEncoder()
            .encodeToString((username + ":" + apiToken).getBytes(StandardCharsets.UTF_8));
        return "Basic " + token;
    }

    private record JiraIssueResponse(String id, String key, String self) {
    }
}
