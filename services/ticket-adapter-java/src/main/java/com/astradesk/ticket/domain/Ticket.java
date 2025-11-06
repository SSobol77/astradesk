package com.astradesk.ticket.domain;

import java.time.Instant;
import java.util.Objects;

import org.springframework.data.annotation.Id;
import org.springframework.data.relational.core.mapping.Column;
import org.springframework.data.relational.core.mapping.Table;

/**
 * Persistent representation of a support ticket.
 *
 * <p>The ticket entity only stores information required by the adapter. Jira and
 * Slack integrations may keep additional metadata on their side – in that case we
 * persist the identifiers needed to correlate AstraDesk records with remote ones.</p>
 */
@Table("tickets")
public class Ticket {

    @Id
    private Long id;

    private String title;

    private String body;

    private TicketStatus status;

    @Column("jira_issue_key")
    private String jiraIssueKey;

    @Column("slack_channel")
    private String slackChannel;

    @Column("created_at")
    private Instant createdAt;

    @Column("updated_at")
    private Instant updatedAt;

    public Ticket() {
        // default constructor required by Spring Data
    }

    public Ticket(
        Long id,
        String title,
        String body,
        TicketStatus status,
        String jiraIssueKey,
        String slackChannel,
        Instant createdAt,
        Instant updatedAt
    ) {
        this.id = id;
        this.title = title;
        this.body = body;
        this.status = status;
        this.jiraIssueKey = jiraIssueKey;
        this.slackChannel = slackChannel;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public static Ticket newTicket(String title, String body) {
        Objects.requireNonNull(title, "title must not be null");
        Objects.requireNonNull(body, "body must not be null");
        return new Ticket(
            null,
            title,
            body,
            TicketStatus.NEW,
            null,
            null,
            null,
            null
        );
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getBody() {
        return body;
    }

    public void setBody(String body) {
        this.body = body;
    }

    public TicketStatus getStatus() {
        return status;
    }

    public void setStatus(TicketStatus status) {
        this.status = status;
    }

    public String getJiraIssueKey() {
        return jiraIssueKey;
    }

    public void setJiraIssueKey(String jiraIssueKey) {
        this.jiraIssueKey = jiraIssueKey;
    }

    public String getSlackChannel() {
        return slackChannel;
    }

    public void setSlackChannel(String slackChannel) {
        this.slackChannel = slackChannel;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }
}
