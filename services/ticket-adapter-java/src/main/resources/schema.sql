-- SPDX-License-Identifier: GPL-2.0-only
-- Project: AstraDesk
-- File: services/ticket-adapter-java/src/main/resources/schema.sql
-- Website: https://www.astradesk.dev
-- Repository: https://github.com/SSobol77/astradesk
--
-- Description: Defines an AstraDesk service or persistence interface.
--
-- Copyright (c) 2026 Siergej Sobolewski
--
-- This file is part of AstraDesk.
--
-- AstraDesk is licensed under the GNU General Public License version 2 only.
-- See the LICENSE file in the project root for the full license text.

CREATE TABLE IF NOT EXISTS tickets (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(255) NOT NULL,
  body TEXT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'NEW',
  jira_issue_key VARCHAR(64),
  slack_channel VARCHAR(128),
  created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
