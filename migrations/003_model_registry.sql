-- Model registry: tracks available LLM models and their configuration.

create table if not exists model_registry (
    id uuid primary key default gen_random_uuid(),
    name text not null unique,
    provider text not null check (provider in ('anthropic', 'openai', 'openai_compatible')),
    base_url text,  -- null = use provider default
    api_key_env text not null,  -- env var name, e.g. 'ANTHROPIC_API_KEY'
    priority int not null default 10,  -- lower = preferred
    enabled boolean not null default true,
    max_complexity text not null default 'standard'
        check (max_complexity in ('trivial', 'standard', 'complex')),
    created_at timestamptz not null default now()
);

-- Seed initial models
insert into model_registry (name, provider, base_url, api_key_env, priority, enabled, max_complexity) values
    ('claude-sonnet-4-6', 'anthropic', null, 'ANTHROPIC_API_KEY', 2, true, 'complex'),
    ('claude-haiku-4-5', 'anthropic', null, 'ANTHROPIC_API_KEY', 3, true, 'trivial'),
    ('deepseek-chat', 'openai_compatible', 'https://api.deepseek.com', 'DEEPSEEK_API_KEY', 1, true, 'standard'),
    ('gpt-4o', 'openai', null, 'OPENAI_API_KEY', 4, true, 'complex')
on conflict (name) do nothing;
