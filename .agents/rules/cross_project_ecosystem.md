# Rule: Cross-Project Ecosystem & Link Hygiene

## Purpose
Enforce clean link hygiene, prevent local file path leakage into version control, and govern architectural integration standards across repositories in the `davtoh` ecosystem (specifically `intelligent-tracker` and `enterprise-website`).

## Ecosystem Overview
- **Edge Vision Microservice (`davtoh/intelligent-tracker`):**
  - High-performance, low-latency edge AI computer vision pipeline (FastAPI, OpenCV, ONNX Runtime, YOLOv8/11, OSNet Re-ID).
  - Handles RTSP/NVR camera ingestion, spatial world modeling (`Scene`, `Area`, `Line`), 4-point homography, and local event alerting.
- **Enterprise Central Cloud Hub (`davtoh/enterprise-website`):**
  - Central Django enterprise platform with multi-tenant user authentication, RBAC, i18n language management, video gallery archiving (`video_gallery`), and CRM/ERP integrations.

## Link Hygiene & Path Guidelines
1. **Never Commit Local Absolute Paths:**
   - Do NOT commit machine-specific absolute file paths (`file:///c:/...`, `C:\dev\...`, `/home/user/...`) into Git-tracked Markdown files, code comments, or documentation.
   - Local `file:///` URIs leak machine structure, break on GitHub web, and fail for team members or CI/CD pipelines.
2. **Standard Link Conventions:**
   - **Intra-Repository Links:** Use relative paths (e.g., `[high_objects.py](intelligent_tracker/high_objects.py)` or `[milestone_plan.md](milestone_plan.md)`).
   - **Inter-Repository Links:** Use public GitHub URLs (e.g., `https://github.com/davtoh/enterprise-website` or specific file permalinks).

## Cross-Repository Integration Standards
1. **Decoupled Architecture:**
   - `intelligent-tracker` runs as an autonomous edge daemon; it must never be embedded directly inside Django's WSGI process.
   - Integration happens over clean HTTP REST, WebSockets, and Webhooks.
2. **API Contract & Event Ingestion:**
   - Edge tracker posts alert events and snapshots to `POST /api/v1/security/events/` on `enterprise-website`.
   - Video clips and journey recordings export directly to `enterprise-website/video_gallery` via `POST /api/v1/gallery/upload/`.
3. **Access Control & Clearance Synchronization:**
   - `enterprise-website` manages authoritative user permissions, custom categories, and visitor clearances.
   - Edge tracker caches these into local SQLite `TrackerDB` to guarantee continuous offline operation even if WAN connectivity is interrupted.
