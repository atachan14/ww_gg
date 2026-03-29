-- Provisional schema for persistent-tree storage.
-- This is intentionally simple and JSON-heavy for the first migration.

create table if not exists game_trees (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    role_counts jsonb not null,
    rules jsonb not null,
    ui_state jsonb not null default '{}'::jsonb,
    current_node_id uuid
);

create table if not exists tree_player_configs (
    tree_id uuid not null references game_trees(id) on delete cascade,
    player_index integer not null,
    name text not null,
    primary key (tree_id, player_index)
);

create table if not exists tree_nodes (
    id uuid primary key default gen_random_uuid(),
    tree_id uuid not null references game_trees(id) on delete cascade,
    parent_node_id uuid references tree_nodes(id) on delete set null,
    branch_label text,
    selected_target integer,
    day integer not null,
    phase_key text not null,
    state jsonb not null,
    analysis jsonb not null,
    player_probabilities jsonb not null,
    child_node_ids jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_tree_nodes_tree_id on tree_nodes(tree_id);
create index if not exists idx_tree_nodes_parent_node_id on tree_nodes(parent_node_id);
