package com.astradesk.ticket.web.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Payload received from the frontend when a ticket should be created.
 */
public class TicketRequest {

    @NotBlank
    @Size(max = 255)
    private String title;

    @NotBlank
    private String body;

    @Size(max = 32)
    private String priority;

    @Size(max = 255)
    private String slackChannel;

    public TicketRequest() {
    }

    public TicketRequest(String title, String body, String priority, String slackChannel) {
        this.title = title;
        this.body = body;
        this.priority = priority;
        this.slackChannel = slackChannel;
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

    public String getPriority() {
        return priority;
    }

    public void setPriority(String priority) {
        this.priority = priority;
    }

    public String getSlackChannel() {
        return slackChannel;
    }

    public void setSlackChannel(String slackChannel) {
        this.slackChannel = slackChannel;
    }
}
