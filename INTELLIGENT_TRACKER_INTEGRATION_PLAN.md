# Enterprise Website & Intelligent Tracker Integration Plan
## Edge AI Vision & Spatial Security Hub Integration

---

### 1. Executive Summary

This plan specifies the architecture and phased roadmap for connecting [davtoh/enterprise-website](https://github.com/davtoh/enterprise-website) with [davtoh/intelligent-tracker](https://github.com/davtoh/intelligent-tracker) (Edge AI Vision Microservice).

```mermaid
flowchart TD
    subgraph Edge [Edge Tier: davtoh/intelligent-tracker]
        Cam[CCTV / IP Cameras (Hikvision, Tapo, EZVIZ)] --> Engine[Edge Inference: YOLOv8/11 + OSNet + SORT]
        Engine --> FastAPIServer[FastAPI Edge Daemon: MJPEG & WebSockets]
        LocalDB[(Edge SQLite TrackerDB: Offline Cache)] <--> Engine
    end

    subgraph Hub [Enterprise Cloud Hub: davtoh/enterprise-website]
        Plugin[plugin_registry: intelligent_tracker Plugin]
        SOC[intelligent_tracker_hub: SOC Dashboard & Live Stream Gateway]
        API[rest_api: /api/v1/security/events/]
        Gallery[video_gallery: Security Incident Clips & Zero-Copy Proxy]
        Auth[user_management: Multi-Tenant RBAC]
        Loc[location_management: Sites, Buildings, Cameras]
        CRM[crm: Temporal Visitor Passes & ANPR Whitelist]
        i18n[language_management: Bilingual Notifications (EN / ES)]
    end

    FastAPIServer -->|Authenticated Live MJPEG Proxy| SOC
    FastAPIServer -->|Real-time Bounding Box Telemetry| SOC
    Engine -->|Webhook Security Alerts (HMAC-SHA256)| API
    Engine -->|Zero-Copy Video Registration| Gallery
    CRM -->|ETag Delta-Sync Whitelist & Vectors| LocalDB
    Engine -->|Access Granted / Arrival Webhook| CRM
    Loc -->|Camera & Site Hierarchy| SOC
```

---

### 2. Integration Architecture & Protocols

#### A. Edge-to-Hub Security Webhook
- **Endpoint:** `POST /api/v1/security/events/` (handled in `rest_api` / `intelligent_tracker_hub`).
- **Authentication:** HMAC SHA-256 header (`X-Tracker-Signature`) validated against shared site secret using constant-time comparison (`hmac.compare_digest`).
- **Payload Schema:**
  - `event_id`: Unique UUID.
  - `event_type`: `IntrusionAlert`, `RestrictedEntityAlert`, `OccupancyThresholdEvent`, `FallDetectedAlert`, `LoiteringAlert`, `LineCrossAlert`.
  - `site_id`: Mapped to `location_management.models.Location`.
  - `camera_id`: Source camera feed identifier.
  - `timestamp`: UTC ISO-8601 timestamp.
  - `snapshot_base64`: JPEG evidence crop of the event.
  - `metadata`: Zone name, dwell duration, confidence score, recognized entity ID/name, homography coordinates.

#### B. Video Evidence Archiving & Zero-Copy Stream Gateway (`video_gallery`)
- **Zero-Copy Lightweight Registration:**
  - When an intrusion occurs or an operator exports a trajectory journey, the edge node registers clip metadata without uploading heavy MP4 bytes:
    `POST /api/v1/gallery/register/`
  - Stores remote edge URL (`source_url`), ground-plane homography coordinates (Milestone 8), camera ID, and duration.
  - Automatically binds a new `VideoItem` under the site's `VideoGallery` (e.g. slug: `security-audit-<site>`) and links to `SecurityEvent`.
- **On-Demand Streaming Reverse Proxy Gateway:**
  - Browser/web clients consume the video via the Hub's streaming proxy gateway:
    `GET /api/v1/gallery/stream/<video_id>/`
  - Forwards HTTP 206 Partial Content / Range requests to the edge node, enabling instant scrubbing/playback without exposing private edge LAN IPs or duplicating video files on Hub disk.
- **Dual-Mode On-Demand Cloud Archival:**
  - For legal/compliance holds or confirmed security incidents, operators can click 'Archive to Cloud Vault' (or call `POST /api/v1/gallery/archive/<video_id>/`) to asynchronously pull and freeze the MP4 into the central Hub vault.
  - Includes atomic staging, SHA-256 checksum verification, and `?force=true` repair from source.
- **Backward-Compatible Multipart Upload:**
  - Traditional edge clip upload remains supported for isolated nodes:
    `POST /api/v1/gallery/upload/`

#### C. Central Multi-Site Dashboard & Live Stream Proxy Gateway (Phase E3 - Frontier SOTA)
- **Live Stream Reverse Proxy Gateway:**
  - Solves the "NAT/Firewall Trap": Browsers cannot reach edge camera streams hosted on internal private LANs (`192.168.x.x`).
  - Hub exposes: `GET /api/v1/security/stream/live/<camera_id>/`
  - Forwards `multipart/x-mixed-replace; boundary=frame` MJPEG chunks from the edge node to authenticated Hub operators, protecting edge nodes from WAN exposure and client multiplexing overload.
- **Camera Registry & Dynamic Health Heartbeats:**
  - Dedicated `Camera` model linked to `location_management.Location` with fields: `camera_id`, `name`, `stream_url`, `status` (`ONLINE`, `OFFLINE`, `CONNECTING`, `DEGRADED`), `last_heartbeat`, `fps`, and `resolution`.
  - Edge nodes emit periodic heartbeat pings:
    `POST /api/v1/security/cameras/heartbeat/` with status, drop rate, and active tracker count.
- **Real-Time Telemetry & Canvas Overlay:**
  - Endpoint: `GET /api/v1/security/stream/telemetry/<camera_id>/` (SSE or polling).
  - High-performance HTML5 Canvas layered directly over the MJPEG canvas rendering 30fps bounding boxes (`[ymin, xmin, ymax, xmax]`), track IDs, dwell indicators, and color-coded entity status (Green = Staff/VIP, Yellow = Visitor, Red = Intrusion/Restricted).
- **Mock Stream & Canvas Test Loop:**
  - Built-in synthetic MJPEG stream generator and telemetry mock loop allowing local development, CI/CD testing, and offline demos without requiring physical cameras.
- **Real-time Alert Feed & Audio Alarm:**
  - Live toast notifications and audible alert chime (via Web Audio API) with instant one-click drilldown to `/security/events/<uuid>/`.

#### D. CRM Visitor Pass & Bi-directional Whitelist Synchronization (Phase E4 - Frontier SOTA)
- **Authoritative Database & Extended Credentials:**
  - `enterprise_website`'s `crm.Contact` acts as the single source of truth for physical access control.
  - Extended contact credentials:
    - `security_clearance`: Choices (`VIP`, `STAFF`, `CONTRACTOR`, `VISITOR`, `RESTRICTED`, `BANNED`).
    - `valid_from` & `valid_until`: Time-bound validity window for temporary contractor passes and guest clearances.
    - `license_plate`: Alphanumeric normalized vehicle license plate for ANPR gate recognition.
    - `face_profile_photo`: Biometric reference image for edge facial recognition vector generation.
    - `face_embedding_vector`: Pre-computed 512-d biometric embedding for zero-latency edge startup.
    - `security_tag`: Custom tag for edge tracker classification.
- **ETag & Version-Based Delta-Sync Protocol:**
  - Endpoint: `GET /api/v1/security/whitelist/?site_id={site_id}`
  - Edge nodes provide `If-None-Match: "<version-hash>"` or `?since=<timestamp>`.
  - Hub computes an MD5/SHA-256 hash of active site credentials. If unchanged, returns `HTTP 304 Not Modified` with 0-byte payload, eliminating WAN bandwidth overhead.
  - If modified, returns only active, non-expired credentials. Expired passes are automatically omitted or marked `REVOKED`.
- **Offline-First Edge Cache (`TrackerDB`):**
  - Edge nodes cache the synchronized whitelist in local SQLite `TrackerDB`, guaranteeing autonomous gate operation and access control during WAN outages.
- **Bi-directional Access Loop & CRM Presence Tracking:**
  - When an edge node identifies an authorized face or vehicle plate, it triggers:
    `POST /api/v1/security/access/`
  - Records an access log entry and updates the contact's CRM status to "On-Premises" / "Checked In".
  - Dispatches bilingual host arrival notifications (EN/ES) via `language_management`.

#### E. Localization & Multi-Language Alerts (`language_management`)
- Incoming alerts and visitor notifications are rendered in the recipient's preferred language using `language_management` catalogs (`en`, `es`, `fr`, `it`, `ja`, `pt`).
- Dispatches localized emails, SMS, and Telegram notifications.

---

### 3. Phased Implementation Roadmap

- **Phase E1: Security REST API & Plugin Scaffold** *(Completed)*
  - Create `intelligent_tracker_hub` app under `plugin_registry`.
  - Implement `POST /api/v1/security/events/` webhook receiver and audit model `SecurityAuditLog`.
  - Configure HMAC-SHA256 signature verification protocol (`X-Tracker-Signature`).
  - Add `Location` model in `location_management`.
  - Build initial SOC Dashboard (`/security/`) and event detail inspection view.

- **Phase E2: Video Gallery Auto-Ingestion & Zero-Copy Stream Gateway** *(Completed)*
  - Implement zero-copy registration endpoint `POST /api/v1/gallery/register/` storing edge video references.
  - Implement streaming reverse proxy gateway `GET /api/v1/gallery/stream/<video_id>/` supporting HTTP 206 Partial Content / Range requests.
  - Implement on-demand compliance freeze `POST /api/v1/gallery/archive/<video_id>/` with atomic staging and SHA-256 checksums.
  - Implement direct multipart upload `POST /api/v1/gallery/upload/` for backward compatibility.
  - Auto-bind to `video_gallery.models.VideoGallery` and link to `SecurityEvent`.
  - Embed zero-copy video player, homography trajectory indicator, and cloud archive/repair action in `event_detail.html`.

- **Phase E3: Central Multi-Site Dashboard, Live Stream Gateway & Telemetry Canvas** *(Completed)*
  - **Data Model:** Create `Camera` model linked to `location_management.Location` with stream endpoints, telemetry resolution, and heartbeat state.
  - **Live Stream Proxy:** Implement `GET /api/v1/security/stream/live/<camera_id>/` proxying edge MJPEG feeds across NAT/WAN firewalls.
  - **Heartbeat & Health API:** Implement `POST /api/v1/security/cameras/heartbeat/` for camera online/offline/degraded state tracking.
  - **Telemetry Stream API:** Implement `GET /api/v1/security/stream/telemetry/<camera_id>/` delivering real-time bounding boxes and track labels.
  - **Mock Stream Generator:** Implement synthetic MJPEG frame generator and telemetry test loop for offline edge simulation and CI/CD testing.
  - **SOC Dashboard UI:** Modernize `/security/` with:
    - Multi-site selector (`location_management.Location`).
    - Multi-camera responsive grid (1x1, 2x2, 3x3 layout matrix).
    - HTML5 Canvas overlay rendering live bounding boxes over video streams.
    - Live camera connection health indicators.
    - Live toast incident feed with Web Audio API chime toggle.

- **Phase E4: CRM Visitor Pass & Bi-directional Whitelist Synchronization** *(Completed)*
  - **CRM Contact Credentials:** Extended `crm.models.Contact` with `security_clearance` (`VIP`, `STAFF`, `CONTRACTOR`, `VISITOR`, `RESTRICTED`, `BANNED`), `valid_from`, `valid_until`, `license_plate` (normalized alphanumeric), `face_profile_photo`, `face_embedding_vector` (512-d float list), `security_tag`, `presence_status` (`on_premises`, `off_premises`), `last_seen_at`, and `last_seen_location`. Added helper methods: `is_pass_valid()`, `normalized_license_plate()`, `check_in()`, and `check_out()`.
  - **Whitelist Delta-Sync API:** Implemented `GET /api/v1/security/whitelist/?site_id={site_id}` with HTTP ETag (`If-None-Match`), `304 Not Modified`, and `?since=` delta-sync filtering to minimize WAN bandwidth. Filters out expired passes and marks banned entities.
  - **Access Log Ingestion API:** Implemented `POST /api/v1/security/access/` recording gate access events in `VisitorAccessLog`, updating CRM contact presence to "On-Premises" (or "Off-Premises" on exit), appending `SECURITY_ACCESS` touchpoints in `InteractionLog`, and escalating banned/restricted intrusion attempts to `SecurityEvent` (`RESTRICTED_ENTITY`, `CRITICAL`).
  - **Offline SQLite Schema Spec:** Created comprehensive offline-first DDL and synchronization protocol in `documentation/INTELLIGENT_TRACKER_OFFLINE_DB_SPEC.md` covering schema DDL, indexing, offline decision flowchart, and transactional outbox.
  - **Automated Localization Dispatch:** Implemented `intelligent_tracker_hub.notifications.send_visitor_arrival_notification` dispatching bilingual host arrival notifications (EN/ES).
  - **UI Modernization:** Modernized CRM Contact views (`contact_detail.html`, `contact_form.html`, `contact_list.html`) and SOC Operations Dashboard (`dashboard.html`) with access history, clearance badges, license plate pills, and live presence indicators.
  - **Comprehensive Test Suite:** 41 passed tests in `tests/test_intelligent_tracker_hub.py`, 23 passed tests in `tests/test_crm.py`, and 271 passed tests repository-wide (100% pass rate).

