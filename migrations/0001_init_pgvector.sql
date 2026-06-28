-- SPDX-License-Identifier: GPL-2.0-only
-- Project: AstraDesk
-- File: migrations/0001_init_pgvector.sql
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

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  chunk TEXT NOT NULL,
  embedding vector(384),        -- all-MiniLM-L6-v2 ma 384
  created_at TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS dialogues (
  id BIGSERIAL PRIMARY KEY,
  agent TEXT NOT NULL,
  query TEXT NOT NULL,
  answer TEXT NOT NULL,
  meta JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audits (
  id BIGSERIAL PRIMARY KEY,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);
