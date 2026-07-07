---
title: Dual Review Test — PRD
---

## Summary
Test PRD for verifying dual review behavior with new comment posting.

## Problem Statement
We need to validate that PRD and design reviews produce separate comments.

## Goals
1. Verify separate comment posting
2. Verify incremental review on file updates

## User Stories
- As a QE engineer, I want each review type to post its own comment

## Acceptance Criteria
- PRD review posts ## AI EP Review comment
- Design review posts ## AI Design Review comment
- Updating one file only triggers that file's review
