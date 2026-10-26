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
- **Endpoint:** POST /api/v1/security/events/ (handled in est_api).
- **Authentication:** HMAC SHA-256 header (X-Tracker-Signature) validated against shared site secret.
- **Payload Schema:**
  - event_id: Unique UUID.
  - event_type: IntrusionAlert, RestrictedEntityAlert, OccupancyThresholdEvent, FallDetectedAlert.
  - site_id: Mapped to location_management.models.Location.
  - camera_id: Source camera feed identifier.
  - 	imestamp: UTC ISO-8601 timestamp.
  - snapshot_base64: JPEG evidence crop of the event.
  - metadata: Zone name, dwell duration, confidence score, recognized entity ID/name.

#### B. Video Evidence Archiving (ideo_gallery)
- When an intrusion occurs or an operator exports a person's trajectory journey:
  - intelligent-tracker uploads the sliced MP4 video to:
    POST /api/v1/gallery/upload/
  - A new VideoItem is automatically registered under the site's VideoGallery (e.g. slug: security-audit-north).
  - Automatically tagged with entity name, camera sequence, and severity badge.

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

- **Phase E2: Video Gallery Auto-Ingestion**
  - Implement secure API endpoint POST /api/v1/gallery/upload/ accepting MP4 uploads from edge nodes.
  - Auto-generate thumbnails and bind to ideo_gallery.models.VideoGallery.

- **Phase E3: Central Multi-Site Dashboard & Live Stream Embed**
  - Django view embedding the live edge MJPEG canvas with WebSocket telemetry overlay.
  - Multi-site selector linked to location_management.

- **Phase E4: CRM Visitor Pass Synchronization**
  - Add facial photo & license plate fields to CRM contact models.
  - Expose /api/v1/security/whitelist/ endpoint for edge synchronization.
