-- Multi-judge quality system: judgments table + task columns

create table if not exists judgments (
    id uuid primary key default gen_random_uuid(),
    task_id uuid references tasks(id) on delete cascade,
    attempt int not null default 1,
    verdict text not null,
    reason text,
    scores jsonb not null default '[]'::jsonb,
    total_judge_cost float default 0.0,
    created_at timestamptz default now()
);

create index if not exists idx_judgments_task_id on judgments(task_id);

alter table tasks add column if not exists task_type text default 'general';
alter table tasks add column if not exists agent_name text;
