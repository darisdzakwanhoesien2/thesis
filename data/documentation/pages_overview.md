# 📘 Application Page Documentation

## 📄 Main Streamlit Application

**File:** `app.py`

**Purpose**  
Serves as the primary entry point for the Streamlit UI, facilitating prompt engineering playground tasks and Mistral OCR processing.

**Inputs**  
PDF files, user-defined system and user prompts, Mistral and OpenRouter API keys.

**Outputs / Visuals**  
Interactive model responses, OCR text extractions, and structured prompt experiment results.

**When to use**  
Exploration and prompt engineering stages.

---

## 📄 ABSA Playground

**File:** `pages/0_ABSA_Playground.py`

**Purpose**  
Provide an interactive environment to test and refine Aspect-Based Sentiment Analysis (ABSA) models and prompts.

**Inputs**  
Text datasets, zero-shot, few-shot, and Chain-of-Thought prompt templates.

**Outputs / Visuals**  
Extracted aspects, entities, and sentiment labels for individual text inputs.

**When to use**  
Modeling and exploration stages.

---

## 📄 Combined ABSA Analysis

**File:** `pages/0_combined_absa.py`

**Purpose**  
Perform integrated Aspect-Based Sentiment Analysis by combining multiple processing steps or models.

**Inputs**  
Text datasets or intermediate analysis files.

**Outputs / Visuals**  
Consolidated ABSA result tables.

**When to use**  
Modeling and analysis stages.

---

## 📄 Combined ABSA All PDF

**File:** `pages/0_combined_absa_all_pdf.py`

**Purpose**  
Execute ABSA analysis across entire collections of PDF documents simultaneously.

**Inputs**  
Directory of PDF files, extraction models.

**Outputs / Visuals**  
Aggregated ABSA metrics across all provided PDF documents.

**When to use**  
Preprocessing and batch analysis stages.

---

## 📄 ABSA Agreement Viewer

**File:** `pages/1_absa_agreement_viewer.py`

**Purpose**  
Visualize and compare the agreement between different ABSA results or model outputs.

**Inputs**  
Multiple sets of ABSA labeling results.

**Outputs / Visuals**  
Agreement visualization charts and consistency metrics.

**When to use**  
Evaluation and validation stages.

---

## 📄 ABSA Entity Mapping Analysis

**File:** `pages/1_absa_entity_mapping_analysis.py`

**Purpose**  
Analyze and visualize how entities are mapped to specific aspects during the ABSA process.

**Inputs**  
ABSA output data, entity lists.

**Outputs / Visuals**  
Mapping tables and entity-aspect correlation charts.

**When to use**  
Auditing and validation stages.

---

## 📄 Results Viewer

**File:** `pages/1_results.py`

**Purpose**  
Display and explore the output data generated from various analysis runs.

**Inputs**  
Processed datasets, JSON or CSV result files.

**Outputs / Visuals**  
Searchable tables and performance summary dashboards.

**When to use**  
Reporting and evaluation stages.

---

## 📄 Bulk Pages Processor

**File:** `pages/2_bulk_pages.py`

**Purpose**  
Process large volumes of document pages sequentially for data extraction or analysis.

**Inputs**  
Multi-page PDF documents or image sets.

**Outputs / Visuals**  
Page-wise extracted data and text results.

**When to use**  
Preprocessing stage.

---

## 📄 Bulk Pages Multiple Method

**File:** `pages/3_bulk_pages_multiple_method.py`

**Purpose**  
Compare the performance of multiple processing methods or models on bulk page data.

**Inputs**  
Document pages, multiple API or model configurations.

**Outputs / Visuals**  
Side-by-side comparison tables and method performance metrics.

**When to use**  
Modeling and evaluation stages.

---

## 📄 OpenRouter Activity Monitor

**File:** `pages/4_openrouter_activity.py`

**Purpose**  
Track, monitor, and audit LLM API activity and associated costs.

**Inputs**  
API usage logs, token consumption data.

**Outputs / Visuals**  
Cost tracking dashboards and token usage alerts.

**When to use**  
Monitoring and auditing stages.

---

## 📄 ABSA Experiment Set Overview

**File:** `pages/5_absa_experiment_set_overview.py`

**Purpose**  
Provide a high-level overview of various ABSA experiment groups and their configurations.

**Inputs**  
Experiment metadata, configuration logs.

**Outputs / Visuals**  
Summary table of experiment parameters and high-level results.

**When to use**  
Evaluation and reporting stages.

---

## 📄 Markdown Processor

**File:** `pages/5_markdown_processor.py`

**Purpose**  
Format and clean raw text or OCR output into structured Markdown documents.

**Inputs**  
Raw text, OCR results, regex-based cleanup rules.

**Outputs / Visuals**  
Formatted Markdown files ready for LLM consumption.

**When to use**  
Preprocessing stage.

---

## 📄 Bulk OCR

**File:** `pages/6_Bulk_OCR.py`

**Purpose**  
Perform batch Optical Character Recognition on multiple files.

**Inputs**  
Multiple PDF or image files.

**Outputs / Visuals**  
ZIP download of text results, progress bar updates.

**When to use**  
Preprocessing stage.

---

## 📄 ABSA Mapping Inspector

**File:** `pages/6_absa_mapping_inspector.py`

**Purpose**  
Perform detailed inspection and auditing of how specific entities are mapped in ABSA results.

**Inputs**  
ABSA result data, mapping definitions.

**Outputs / Visuals**  
Inspection tables and detailed error alerts.

**When to use**  
Auditing and validation stages.

---

## 📄 Bulk PDF Multiple Methods

**File:** `pages/7_bulk_pdf_multiple_methods.py`

**Purpose**  
Evaluate and compare various PDF extraction and analysis methods across a set of documents.

**Inputs**  
Collection of PDF files, multiple model/prompt configurations.

**Outputs / Visuals**  
Comparative performance charts and side-by-side result datasets.

**When to use**  
Evaluation and modeling stages.

---

## 📄 Data Explorer

**File:** `pages/8_data.py`

**Purpose**  
Explore, manage, and export datasets used or produced by the application.

**Inputs**  
Local CSV/JSONL files, logged playground interactions.

**Outputs / Visuals**  
Data tables, summary statistics, and JSONL exports for fine-tuning.

**When to use**  
Exploration and preprocessing stages.

---

## 📄 Framework Mapping Audit

**File:** `pages/8_framework_mapping_audit.py`

**Purpose**  
Validate and audit analysis results against specific domain frameworks such as ESG or policy guidelines.

**Inputs**  
ABSA results, domain-specific framework guidelines.

**Outputs / Visuals**  
Audit reports, error labels, and framework alignment scores.

**When to use**  
Auditing and reporting stages.

---

## 📄 Few-shot Editor Module

**File:** `ui/fewshot.py`

**Purpose**  
Provide a UI component for entering and managing few-shot examples, including reasoning steps.

**Inputs**  
User-provided Question/Answer pairs and reasoning/Chain-of-Thought steps.

**Outputs / Visuals**  
Structured few-shot message blocks for LLM prompt injection.

**When to use**  
Modeling and prompt design stages.

---
