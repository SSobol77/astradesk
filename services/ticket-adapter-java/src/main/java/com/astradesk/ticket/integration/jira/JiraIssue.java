package com.astradesk.ticket.integration.jira;

/**
 * Lightweight projection of data returned by Jira when an issue is created.
 */
public record JiraIssue(String id, String key, String selfUrl) {
}
