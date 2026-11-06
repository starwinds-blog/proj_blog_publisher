export interface StorySummary {
  slug: string;
  title: string;
  stage: 'raw' | 'draft' | 'approved' | 'staged' | 'pending_verification' | 'published' | 'deploy_failed';
  template: string;
  tags: string[];
  date: string;
  description: string;
  raw_file?: string | null;
  draft_file?: string | null;
  approved_file?: string | null;
  site_file?: string | null;
  url?: string | null;
  commit_sha?: string | null;
  updated_at?: string;
  validation_valid?: boolean | null;
  validation_errors_count?: number;
  validation_warnings_count?: number;
}

export interface ValidationReport {
  valid: boolean;
  file: string;
  checked_at: string;
  errors: string[];
  warnings: string[];
  checks: {
    front_matter_valid: boolean;
    code_blocks_balanced: boolean;
    links_and_images_valid: boolean;
    no_secrets_found: boolean;
    raw_code_preserved: boolean;
  };
  front_matter: Record<string, unknown>;
}

export interface ReviewReport {
  slug: string;
  title: string;
  template: string;
  raw_file: string;
  draft_file: string;
  created_at: string;
  change_summary?: {
    grammar_and_structure: string[];
    fact_check_items: string[];
    suggestions: string[];
  };
  diff?: string;
}

export interface StoryDetail {
  summary: StorySummary;
  raw_content: string;
  draft_markdown: string;
  front_matter: {
    title?: string;
    date?: string;
    draft?: boolean;
    description?: string;
    tags?: string[];
    categories?: string[];
    slug?: string;
  };
  body_markdown: string;
  review_report: ReviewReport;
  validation?: ValidationReport | null;
  publication_record?: Record<string, unknown> | null;
}

export interface PublishingConfig {
  site_title: string;
  site_description: string;
  author_name: string;
  language_code: string;
  github_owner: string;
  github_repo: string;
  repo_type: string;
  base_url: string;
  branch: string;
  default_dry_run: boolean;
  approval_mode: string;
}

export interface OverviewResponse {
  server_time_kst: string;
  env: {
    os: string;
    project_root: string;
    tools: Record<string, { name: string; installed: boolean; required: boolean; version: string | null }>;
    site: {
      hugo_toml_exists: boolean;
      workflow_exists: boolean;
      github_owner: string;
      github_repo: string;
      repo_type: string;
      base_url: string;
      remote_configured: boolean;
    };
    ready_for_local_mvp: boolean;
    ready_for_public_publish: boolean;
    blockers: string[];
    warnings: string[];
  };
  counts: {
    total: number;
    raw: number;
    draft: number;
    approved: number;
    staged: number;
    pending_verification: number;
    published: number;
  };
  stories: StorySummary[];
  publishing_config: PublishingConfig;
  recent_logs: {
    id: number;
    slug: string;
    action: string;
    status: string;
    summary: string;
    created_at: string;
  }[];
}
