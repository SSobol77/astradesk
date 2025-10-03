package com.astradesk.ticket.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.relational.core.mapping.Table;

@Table("tickets")
public class Ticket {
  @Id
  private Long id;
  private String title;
  private String body;

  public Ticket() {}
  public Ticket(String title, String body) { this.title = title; this.body = body; }

  public Long getId() { return id; }
  public String getTitle() { return title; }
  public String getBody() { return body; }

  public void setId(Long id) { this.id = id; }
  public void setTitle(String t) { this.title = t; }
  public void setBody(String b) { this.body = b; }
}
