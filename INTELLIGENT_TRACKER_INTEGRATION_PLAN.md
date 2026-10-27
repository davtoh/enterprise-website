# Enterprise Website & Intelligent Tracker Integration Plan
## Edge AI Vision & Spatial Security Hub Integration

---

### 1. Executive Summary

This plan specifies the architecture and phased roadmap for connecting [davtoh/enterprise-website](https://github.com/davtoh/enterprise-website) with [davtoh/intelligent-tracker](https://github.com/davtoh/intelligent-tracker) (Edge AI Vision Microservice).

`mermaid
flowchart TD
    subgraph Edge [Edge Tier: davtoh/intelligent-tracker]
        Cam[CCTV / IP Cameras (Hikvision, Tapo, EZVIZ)] --> Engine[Edge Inference (YOLOv8/11 + OSNet + SORT)]
        Engine --> FastAPIServer[FastAPI Edge Daemon (MJPEG & WebSockets)]
    end

    subgraph Hub [Enterprise Cloud Hub: davtoh/enterprise-website]
        Plugin[plugin_registry: intelligent_tracker Plugin]
        API[rest_api: /api/v1/security/events/]
        Gallery[video_gallery: Security Incident Clips & Journeys]
        Auth[user_management: Multi-Tenant RBAC]
        Loc[location_management: Sites, Buildings, Floors]
        CRM[crm: Visitor Passes & VIP Clearances]
        i18n[language_management: Bilingual Notifications (EN / ES)]
    end

    FastAPIServer -->|Real-time MJPEG Canvas| Plugin
    Engine -->|Webhook Security Alerts| API
    Engine -->|Exported Journey MP4 Clips| Gallery
    CRM -->|Authorized Whitelist & Tags| Engine
    Loc -->|Camera Hierarchy| Plugin
`

---

### 2. Integration Architecture & Protocols

#### A. Edge-to-Hub Security Webhook
- **Endpoint:** POST /api/v1/security/events/ (handled in 
est_api).
- **Authentication:** HMAC SHA-256 header (X-Tracker-Signature) validated against shared site secret.
- **Payload Schema:**
  - event_id: Unique UUID.
  - event_type: IntrusionAlert, RestrictedEntityAlert, OccupancyThresholdEvent, FallDetectedAlert.
  - site_id: Mapped to location_management.models.Location.
  - camera_id: Source camera feed identifier.
  - 	imestamp: UTC ISO-8601 timestamp.
  - snapshot_base64: JPEG evidence crop of the event.
  - metadata: Zone name, dwell duration, confidence score, recognized entity ID/name.

#### B. Video Evidence Archiving & Zero-Copy Stream Gateway (video_gallery)
- **Zero-Copy Lightweight Registration:**
  - When an intrusion occurs or an operator exports a trajectory journey, the edge node registers the clip metadata without uploading heavy MP4 bytes:
    POST /api/v1/gallery/register/
  - Stores the remote edge URL (source_url), ground-plane homography coordinates (from Milestone 8), camera ID, and duration.
  - Automatically binds a new VideoItem under the site's VideoGallery (e.g. slug: security-audit-north) and links to SecurityEvent.
- **On-Demand Streaming Reverse Proxy Gateway:**
  - Browser/web clients consume the video via the Hub's streaming proxy gateway:
    GET /api/v1/gallery/stream/<video_id>/
  - Forwards HTTP 206 Range requests to the edge node, enabling instant scrubbing/playback without exposing private edge LAN IPs or duplicating video files on the Hub's disk.
- **Dual-Mode On-Demand Cloud Archival:**
  - For legal/compliance holds or confirmed security incidents, operators can click 'Archive to Cloud Vault' (or call POST /api/v1/gallery/archive/<video_id>/) to asynchronously pull and freeze the MP4 into the central Hub vault.
- **Backward-Compatible Multipart Upload:**
  - Traditional edge clip upload remains supported for isolated nodes:
    POST /api/v1/gallery/upload/

#### C. Two-Way Visitor & Whitelist Sync (crm)
- enterprise-website maintains the authoritative database of authorized personnel, VIPs, contractors, and family vehicles.
- Edge trackers fetch updates from:
  GET /api/v1/security/whitelist/?site_id={site_id}
- Cached into local edge SQLite TrackerDB so AI detection continues uninterrupted during WAN outages.

#### D. Localization & Multi-Language Alerts (language_management)
- Incoming alerts are rendered in the recipient's preferred language using language_management catalogs (es, en).
- Dispatches localized emails, SMS, and Telegram notifications.

---

### 3. Phased Implementation Roadmap

- **Phase E1: Security REST API & Plugin Scaffold**
  - Create intelligent_tracker_hub app under plugin_registry.
  - Implement POST /api/v1/security/events/ webhook receiver and audit model SecurityAuditLog.
  - Configure HMAC signature verification.

- **Phase E2: Video Gallery Auto-Ingestion & Zero-Copy Stream Gateway**
  - Implement zero-copy registration endpoint POST /api/v1/gallery/register/ storing edge video references.
  - Implement streaming reverse proxy gateway GET /api/v1/gallery/stream/<video_id>/ supporting HTTP 206 Partial Content / Range requests.
  - Implement on-demand compliance freeze POST /api/v1/gallery/archive/<video_id>/.
  - Implement direct multipart upload POST /api/v1/gallery/upload/ for backward compatibility.
  - Auto-bind to ideo_gallery.models.VideoGallery and link to SecurityEvent.

- **Phase E3: Central Multi-Site Dashboard & Live Stream Embed**
  - Django view embedding the live edge MJPEG canvas with WebSocket telemetry overlay.
  - Multi-site selector linked to location_management.

- **Phase E4: CRM Visitor Pass Synchronization**
  - Add facial photo & license plate fields to CRM contact models.
  - Expose /api/v1/security/whitelist/ endpoint for edge synchronization.
