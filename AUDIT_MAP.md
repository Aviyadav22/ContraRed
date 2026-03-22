# ContraRed Audit Map

## AUDIT-1: Backend Services Layer (37 files, 198+ functions)

### ai_service.py — Multi-Provider AI Integration
| Function | Description | Workflow |
|----------|-------------|----------|
| `AIService.explain_risk()` | Generate plain-English explanation of a contract risk using Gemini/Azure | ai-provider |
| `AIService.suggest_fix()` | Generate suggested revisions for flagged risks | redline-generation |
| `AIService.enrich_match()` | Enhance rule match with AI context and business implications | ai-provider |
| `AIService.summarize_contract()` | Create executive summary of full contract with key terms | ai-provider |
| `AIService.suggest_fix_with_playbook()` | Generate revisions aligned with playbook language and position | redline-generation |

### analysis_pipeline.py — 5-Stage Analysis Orchestration
| Function | Description | Workflow |
|----------|-------------|----------|
| `AnalysisPipeline.analyze()` | Execute full 3-layer analysis (structure→rules→redlines) with hallucination detection | document-analysis |
| `AnalysisPipeline._verify_redlines()` | Post-generation verification of AI output against contract text | hallucination-detection |
| `AnalysisPipeline._score_confidence()` | Apply 5-factor confidence scoring to all redlines | confidence-scoring |
| `AnalysisPipeline._resolve_dependencies()` | Apply cascading risk escalations and suppressions | dependency-resolution |
| `AnalysisPipeline._apply_scope_analysis()` | Analyze breadth/mutuality/exposure for scope-based risk adjustment | scope-analysis |

### analytics_service.py — Organization-Level Analytics
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_org_overview()` | Fetch documents analyzed, total risks, and red/yellow breakdowns | analytics |
| `get_risk_breakdown()` | Calculate risk distribution across risk levels and categories | analytics |
| `get_user_activity()` | Track per-user review counts and performance metrics | analytics |
| `get_trend_data()` | Historical trend data (weekly/monthly) for risk and volume patterns | analytics |
| `get_executive_dashboard()` | Board-ready KPI summary with ROI and team performance | analytics |
| `get_bi_export_data()` | Full-export data for BI integration (Tableau, Power BI) | reporting |

### benchmark_service.py — Risk Benchmarking & Comparison
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_document_percentile()` | Calculate where this document ranks against portfolio | benchmarking |
| `get_portfolio_risk()` | Overall portfolio risk summary with high-risk contracts list | benchmarking |
| `get_clause_analytics()` | Per-clause-type risk rankings across portfolio | benchmarking |
| `get_team_performance()` | Per-reviewer speed, accuracy, and risk detection rates | benchmarking |
| `refresh_benchmark_profiles()` | Recompute all portfolio percentiles after new analyses | benchmarking |

### cache_service.py — Redis-Based Caching (Tenant-Isolated)
| Function | Description | Workflow |
|----------|-------------|----------|
| `CacheService.connect/disconnect()` | Initialize/close Redis connection | caching |
| `CacheService.get/set/delete()` | Key-value ops with org isolation | caching |
| `CacheService.delete_org_keys()` | Bulk-delete all keys for an organization | caching |
| `CacheService.make_analysis_key/make_clause_key()` | Generate org-isolated cache keys | caching |

### clause_classifier.py — Clause Categorization
| Function | Description | Workflow |
|----------|-------------|----------|
| `ClauseClassifier.classify()` | Detect clause type (e.g., "liability_cap") from text | clause-classification |
| `ClauseClassifier.classify_batch()` | Classify multiple clause snippets in bulk | clause-classification |

### confidence_scorer.py — Multi-Factor Confidence Scoring
| Function | Description | Workflow |
|----------|-------------|----------|
| `ConfidenceScorer.score_redline()` | Calculate confidence (0-1) using 5-factor model | confidence-scoring |
| `ConfidenceScorer.score_batch()` | Score multiple redlines with breakdown details | confidence-scoring |

### contract_differ.py — Contract Comparison
| Function | Description | Workflow |
|----------|-------------|----------|
| `compute_diff()` | Paragraph-by-paragraph diff between two contract versions | document-analysis |
| `compute_diff_with_ai()` | Enhanced diff with AI-assisted section matching | document-analysis |

### defined_terms_resolver.py — Defined Terms Extraction
| Function | Description | Workflow |
|----------|-------------|----------|
| `DefinedTermsResolver.resolve()` | Extract all defined terms and map definitions with circular ref handling | defined-terms |
| `DefinedTermsResolver._check_overbroad()` | Detect overbroad definitions using 10-signal pattern matching | defined-terms |

### dependency_resolver.py — Cross-Clause Risk Cascading
| Function | Description | Workflow |
|----------|-------------|----------|
| `DependencyResolver.resolve()` | Apply rule dependencies to cascade risk escalations/suppressions | dependency-resolution |
| `DependencyResolver._evaluate_trigger()` | Check if dependency trigger condition is met | dependency-resolution |
| `DependencyResolver._apply_effect()` | Apply effect (escalate/suppress/flag) to target rule | dependency-resolution |

### email_service.py — Transactional Email
| Function | Description | Workflow |
|----------|-------------|----------|
| `send_password_reset_email()` | Send password reset link via Resend | email |
| `send_dunning_email()` | Send payment overdue notification | billing |

### fix_verifier.py — AI Fix Verification
| Function | Description | Workflow |
|----------|-------------|----------|
| `FixVerifier.verify_fix()` | Post-generation verification: section refs, length, playbook alignment | hallucination-detection |

### gemini_analyzer.py — AI-First Contract Analysis
| Function | Description | Workflow |
|----------|-------------|----------|
| `GeminiAnalyzer.analyze_full_contract()` | Full AI analysis pipeline with jurisdiction awareness | document-analysis |
| `GeminiAnalyzer.generate_clause()` | AI generation of missing clause based on playbook | ai-provider |
| `GeminiAnalyzer.generate_fix()` | AI-generated revision for flagged risk | redline-generation |
| `GeminiAnalyzer.analyze_clause()` | Deep AI analysis of single clause | ai-provider |
| `GeminiAnalyzer.research_clause()` | Research-mode: explanation + case law references | ai-provider |

### hallucination_guard.py — Post-Generation Verification
| Function | Description | Workflow |
|----------|-------------|----------|
| `HallucinationGuard.verify_quote()` | 4-stage verification (exact→normalized→fuzzy→reject) | hallucination-detection |
| `HallucinationGuard.verify_batch()` | Verify multiple quotes in bulk | hallucination-detection |
| `HallucinationGuard.needs_requery()` | Determine if AI should be re-prompted | hallucination-detection |

### intelligence_bridge.py — Strategy Pattern for Analysis
| Function | Description | Workflow |
|----------|-------------|----------|
| `OmniContextStrategy.analyze()` | Full-doc-to-GPT-4o strategy (small contracts) | document-analysis |
| `HybridSentinelStrategy.analyze()` | Scout/Surgeon two-pass (large contracts) | document-analysis |
| `IntelligenceBridge.get_strategy()` | Factory: select strategy by doc size | document-analysis |

### invoice_pdf.py — Invoice PDF Generation
| Function | Description | Workflow |
|----------|-------------|----------|
| `generate_invoice_pdf()` | Generate single-page invoice PDF | billing |

### issues_exporter.py — Issue Export
| Function | Description | Workflow |
|----------|-------------|----------|
| `export_issues_to_csv()` | Export analysis issues to CSV | reporting |
| `export_issues_to_xlsx()` | Export issues to Excel with color-coded risk levels | reporting |

### jurisdiction_detector.py — Jurisdiction Detection
| Function | Description | Workflow |
|----------|-------------|----------|
| `JurisdictionDetector.detect()` | Identify governing law jurisdiction from text | jurisdiction-detection |
| `apply_jurisdiction_overrides()` | Apply jurisdiction-specific risk adjustments | jurisdiction-detection |

### mfa_service.py — Multi-Factor Authentication
| Function | Description | Workflow |
|----------|-------------|----------|
| `setup_mfa/confirm_mfa_setup/verify_mfa/disable_mfa()` | Full MFA lifecycle | mfa |
| `generate_backup_codes/regenerate_backup_codes()` | Backup code management | mfa |

### pdf_report_generator.py — PDF Report Generation
| Function | Description | Workflow |
|----------|-------------|----------|
| `generate_pdf_report()` | Generate PDF report with risk color coding | reporting |

### playbook_cache.py — Rule Engine Caching
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_default_rule_engine/get_cached_rule_engine()` | Cached RuleEngine instances | caching |
| `invalidate_playbook_cache()` | Clear cache on playbook mutation | caching |

### playbook_conditions_engine.py — Conditional Playbook Logic
| Function | Description | Workflow |
|----------|-------------|----------|
| `ConditionsEngine.process()` | Full condition evaluation and override application | playbook-matching |

### playbook_templates.py — Built-in Playbook Templates
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_default_playbook_data()` | Fetch default playbook template | playbook-matching |
| `get_playbook_by_industry()` | Fetch industry-specific playbook | playbook-matching |

### playbook_versioning.py — Playbook Version Control
| Function | Description | Workflow |
|----------|-------------|----------|
| `create_version_snapshot()` | Create JSON snapshot of playbook state | versioning |
| `rollback_to_version()` | Restore playbook to previous version | versioning |
| `diff_versions()` | Field-level diff between two versions | versioning |

### prompt_templates.py — Structured AI Prompts
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_system_prompt()` | 4-step system prompt (ORIENT→TERMS→RULE-BY-RULE→CROSS-CLAUSE) | prompt-engineering |
| `get_clause_prompt()` | Prompt for single-clause analysis | prompt-engineering |

### redline_implementer.py — Surgical Word-Level Redlines
| Function | Description | Workflow |
|----------|-------------|----------|
| `RedlineImplementer.find_anchor()` | Locate text using hash/exact/fuzzy matching | redline-generation |
| `RedlineImplementer.generate_track_changes_ooxml()` | Generate OOXML Track Changes for word-level diffs | redline-generation |
| `RedlineImplementer.generate_insert_only_ooxml()` | Generate OOXML for missing clause insertion | redline-generation |
| `RedlineImplementer.apply_redline()` | Apply single redline with anchor verification | redline-generation |

### report_generator.py — DOCX Report Generation
| Function | Description | Workflow |
|----------|-------------|----------|
| `generate_risk_report()` | Generate professional risk assessment DOCX | reporting |

### report_service.py — Report Management
| Function | Description | Workflow |
|----------|-------------|----------|
| `generate_report()` | Generate and store report (4 types: executive, gc, team, risk) | reporting |
| `list_reports/get_report()` | CRUD for generated reports | reporting |

### roi_service.py — ROI Calculation
| Function | Description | Workflow |
|----------|-------------|----------|
| `calculate_roi()` | Calculate time savings and monetary ROI | analytics |
| `update_org_benchmarks()` | Update org time/cost benchmarks | analytics |

### rule_engine.py — Pattern-Based Clause Detection
| Function | Description | Workflow |
|----------|-------------|----------|
| `RuleEngine.evaluate()` | Execute all rules against contract text | document-analysis |
| `RuleEngine.from_playbook_rules()` | Build RuleEngine from PlaybookRule objects | playbook-matching |

### rules_library.py — 75 Built-in Rules
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_default_rules()` | Fetch 75 pre-built clause detection rules | playbook-matching |

### scope_analyzer.py — Deterministic Scope Analysis
| Function | Description | Workflow |
|----------|-------------|----------|
| `ScopeAnalyzer.analyze()` | Analyze scope dimensions (breadth, mutuality, exposure, duration, trigger) | scope-analysis |
| `ScopeAnalyzer.get_coverage_report()` | Coverage analysis: which clause types found/missing | scope-analysis |

### sso_service.py — WorkOS-Based SSO
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_authorization_url/handle_sso_callback()` | SSO login flow | sso |
| `enable_sso_for_org/disable_sso_for_org()` | SSO configuration | sso |

### structure_extractor.py — Document Structure Extraction
| Function | Description | Workflow |
|----------|-------------|----------|
| `StructureExtractor.extract_from_docx/extract_from_text()` | Parse document into ContractMap | document-analysis |
| `ContractMap.get_node_by_hash/get_all_text()` | Navigate extracted structure | document-analysis |

### text_normalizer.py — Text Normalization
| Function | Description | Workflow |
|----------|-------------|----------|
| `normalize_text()` | Normalize Word text for regex matching | text-normalization |
| `normalize_for_search()` | Aggressive normalization for search | text-normalization |

### token_service.py — JWT Token Blacklist
| Function | Description | Workflow |
|----------|-------------|----------|
| `TokenBlacklistService.revoke/is_revoked()` | Token blacklisting for logout | token-management |
| `TokenBlacklistService.register_session()` | Enforce concurrent session limits | token-management |
| `TokenBlacklistService.record_login_ip()` | IP tracking for anomaly detection | token-management |
