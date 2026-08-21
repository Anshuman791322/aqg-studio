-- =============================================================================
-- Migration: 20260821000004_hybrid_search_function.sql
-- Description: User-scoped hybrid vector and full-text search SQL function
-- =============================================================================

CREATE OR REPLACE FUNCTION match_document_chunks_hybrid(
    p_user_id UUID,
    p_document_id UUID,
    p_query_text TEXT,
    p_query_embedding VECTOR(384) DEFAULT NULL,
    p_top_k INT DEFAULT 5,
    p_alpha FLOAT DEFAULT 0.5,
    p_section_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    chunk_index INT,
    content TEXT,
    page_start INT,
    page_end INT,
    section TEXT,
    chapter TEXT,
    token_count INT,
    similarity FLOAT,
    lexical_rank FLOAT,
    hybrid_score FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
BEGIN
    RETURN QUERY
    WITH scoped_chunks AS (
        SELECT 
            c.id,
            c.document_id,
            c.chunk_index,
            c.content,
            c.page_start,
            c.page_end,
            c.section,
            c.chapter,
            c.token_count,
            CASE 
                WHEN p_query_embedding IS NOT NULL AND c.embedding IS NOT NULL THEN
                    1 - (c.embedding <=> p_query_embedding)
                ELSE 0.0
            END::FLOAT AS sim,
            CASE 
                WHEN p_query_text IS NOT NULL AND p_query_text <> '' THEN
                    ts_rank_cd(
                        to_tsvector('english', c.content),
                        plainto_tsquery('english', p_query_text)
                    )
                ELSE 0.0
            END::FLOAT AS lex
        FROM document_chunks c
        WHERE c.user_id = p_user_id
          AND c.document_id = p_document_id
          AND (p_section_filter IS NULL OR c.section = p_section_filter)
    )
    SELECT 
        sc.id,
        sc.document_id,
        sc.chunk_index,
        sc.content,
        sc.page_start,
        sc.page_end,
        sc.section,
        sc.chapter,
        sc.token_count,
        sc.sim AS similarity,
        sc.lex AS lexical_rank,
        (
            CASE 
                WHEN p_query_embedding IS NOT NULL THEN (p_alpha * sc.sim + (1.0 - p_alpha) * COALESCE(sc.lex, 0.0))
                ELSE COALESCE(sc.lex, 0.0)
            END
        )::FLOAT AS hybrid_score
    FROM scoped_chunks sc
    ORDER BY hybrid_score DESC, sc.chunk_index ASC
    LIMIT p_top_k;
END;
$$;
