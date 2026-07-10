## 1. Publish date resolution in bridge

- [x] 1.1 Add `PublishDateResolution` dataclass and `resolve_publish_dates()` in `github_pages_publish.py` with `intended_url_date`, `publish_timestamp`, `permalink`, `date_adjusted`, and optional `on_future_date` (`adjust` default, `fail` secondary)
- [x] 1.2 Add stable error code `blog_publish_future_date_requires_scheduled_execution` for `on_future_date` `fail`
- [x] 1.3 Add helpers `intended_permalink(public_slug, intended_url_date)` and `format_jekyll_date(publish_timestamp)`; keep existing `public_url()` using intended URL date
- [x] 1.4 Extend `PublishPlan` with `intended_url_date`, `publish_timestamp`, `date_adjusted`, and `permalink` fields; include in `plan_to_dict` and `print_summary`

## 2. Bridge frontmatter and plan integration

- [x] 2.1 Update `prepare_frontmatter()` to accept `PublishDateResolution` (or equivalent) and emit `date` from publication timestamp plus `permalink` when `date_adjusted`
- [x] 2.2 Update `target_paths()` / `build_plan()` to use intended URL date for `_posts/` filename while using resolution for frontmatter
- [x] 2.3 Update `run_publish()` / CLI to accept injectable `execution_time` and thread resolution through dry-run and apply paths
- [x] 2.4 Update `render_expected_public_post()` and reconciliation helpers to use the same resolution for byte-exact comparisons

## 3. Flow A publish flow integration

- [x] 3.1 Pass `execution_time` from `publish_blog_post()` into `run_publish()` (injectable for tests)
- [x] 3.2 Ensure `source_public_url` and `BlogPublishResult` use bridge `public_url` from intended URL date when dates are adjusted
- [x] 3.3 Expose `date_adjusted` and `publish_timestamp` in `blog_publish` summary metadata when adjustment occurs
- [x] 3.4 Verify publish reconciliation and `already_published` paths still match canonical rendered output with permalink when adjusted

## 4. Automated tests

- [x] 4.1 Test: future intended date + frozen execution time → safe `date`, explicit `permalink`, intended `public_url`
- [x] 4.2 Test: safe intended date → no `permalink`, existing `jekyll_date` behavior unchanged
- [x] 4.3 Test: `_posts/` filename uses intended URL date when publication timestamp is adjusted
- [x] 4.4 Test: post `02-deferring-is-not-avoiding-it-can-be-architecture` regression (`2026-07-10` intended, `2026-07-09T21:08:00-05:00` execution)
- [x] 4.5 Test: `on_future_date` `fail` raises `blog_publish_future_date_requires_scheduled_execution`
- [x] 4.6 Extend `tests/test_blog_publish_flow.py` for adjusted-date publish success and `source_public_url` path
- [x] 4.7 Confirm no changes to LinkedIn publication tests or endpoints

## 5. Operator documentation

- [x] 5.1 Update `docs/workflows/blog-publishing-bridge.md` with Jekyll future-post exclusion, safe publish timestamp vs intended URL date, permalink preservation, and guidance not to manually edit dates after normal Flow A execution
- [x] 5.2 Document optional `on_future_date` `fail` mode for operators who require scheduled execution instead of adjustment

## 6. Validation

- [x] 6.1 Run `pytest` for new and affected tests
- [x] 6.2 Run `openspec validate github-pages-publish-date-safety --strict`
- [x] 6.3 Run `openspec validate --all --strict`
