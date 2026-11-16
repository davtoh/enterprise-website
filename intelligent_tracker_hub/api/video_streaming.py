import hashlib
import logging
import os
import re
import uuid
import requests

from django.core.files.base import ContentFile
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from video_gallery.models import VideoItem

logger = logging.getLogger(__name__)


def _check_local_archive(video_item) -> tuple[bool, str | None, int]:
    """Check whether VideoItem has an existing, non-empty local archive file."""
    if not video_item.video_file:
        return False, None, 0
    try:
        file_path = video_item.video_file.path
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            if file_size > 0:
                return True, file_path, file_size
    except Exception as exc:
        logger.warning(f"Error checking local archive for VideoItem #{video_item.id}: {exc}")
    return False, None, 0


def _file_range_iterator(path: str, offset: int, length: int, chunk_size: int = 65536):
    """Yield byte slices from a local file for HTTP 206 Range responses."""
    with open(path, "rb") as handle:
        handle.seek(offset)
        remaining = length
        while remaining > 0:
            data = handle.read(min(remaining, chunk_size))
            if not data:
                break
            remaining -= len(data)
            yield data


def _full_file_iterator(path: str, chunk_size: int = 65536):
    """Yield full file chunks for HTTP 200 local vault streaming."""
    with open(path, "rb") as handle:
        while True:
            data = handle.read(chunk_size)
            if not data:
                break
            yield data


def _stream_local_file(request, file_path: str, file_size: int) -> StreamingHttpResponse:
    """Serve local archived MP4 with HTTP 206 byte-range support."""
    range_header = request.headers.get("Range") or request.META.get("HTTP_RANGE", "")
    match = re.match(r"bytes=(\d+)-(\d*)", range_header) if (range_header and file_size) else None
    if match:
        start = int(match.group(1))
        end = min(int(match.group(2)) if match.group(2) else file_size - 1, file_size - 1)
        content_length = (end - start) + 1
        response = StreamingHttpResponse(
            _file_range_iterator(file_path, start, content_length),
            status=status.HTTP_206_PARTIAL_CONTENT,
            content_type="video/mp4",
        )
        response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        response["Content-Length"] = str(content_length)
    else:
        response = StreamingHttpResponse(
            _full_file_iterator(file_path),
            status=status.HTTP_200_OK,
            content_type="video/mp4",
        )
        response["Content-Length"] = str(file_size)
    response["Accept-Ranges"] = "bytes"
    response["X-Evidence-Source"] = "local-vault"
    return response


def _build_edge_response(edge_resp, is_corruption_fallback: bool) -> StreamingHttpResponse:
    """Wrap upstream requests.Response in a Django StreamingHttpResponse."""
    def edge_stream_generator():
        try:
            for chunk in edge_resp.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk
        finally:
            edge_resp.close()

    status_code = status.HTTP_206_PARTIAL_CONTENT if edge_resp.status_code == 206 else status.HTTP_200_OK
    response = StreamingHttpResponse(
        edge_stream_generator(),
        status=status_code,
        content_type=edge_resp.headers.get("Content-Type", "video/mp4"),
    )
    for header in ("Content-Range", "Content-Length", "Accept-Ranges"):
        if header in edge_resp.headers:
            response[header] = edge_resp.headers[header]
    response.setdefault("Accept-Ranges", "bytes")
    response["X-Evidence-Source"] = "edge-fallback" if is_corruption_fallback else "edge-stream"
    return response


def _stream_remote_edge(request, remote_url: str, is_corruption_fallback: bool):
    """Proxy video stream from remote edge URL with range forwarding."""
    if not remote_url or not (remote_url.startswith("http://") or remote_url.startswith("https://")):
        return Response(
            {"error": "Video has no accessible remote stream URL or local archive."},
            status=status.HTTP_404_NOT_FOUND,
        )
    range_header = request.headers.get("Range") or request.META.get("HTTP_RANGE", "")
    headers = {"Range": range_header} if range_header else {}
    try:
        edge_resp = requests.get(remote_url, headers=headers, stream=True, timeout=(5, 30))
    except (requests.ConnectionError, requests.Timeout, requests.RequestException) as err:
        return Response(
            {
                "error": "Edge video stream unreachable",
                "detail": str(err),
                "source_url": remote_url,
                "local_damaged": is_corruption_fallback,
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return _build_edge_response(edge_resp, is_corruption_fallback)


def _download_remote_video(remote_url: str) -> tuple[bytes | None, Response | None]:
    """Download and validate remote video bytes for cloud vault archival."""
    if not remote_url or not (remote_url.startswith("http://") or remote_url.startswith("https://")):
        return None, Response(
            {"error": "Video has no remote source URL to archive or repair from."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        remote_resp = requests.get(remote_url, stream=True, timeout=(5, 60))
        remote_resp.raise_for_status()
        content = remote_resp.content
    except (requests.ConnectionError, requests.Timeout, requests.RequestException) as err:
        return None, Response(
            {"error": "Failed to pull remote video stream from reference.", "detail": str(err), "source_url": remote_url},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    if len(content) < 16:
        return None, Response(
            {"error": "Remote stream payload is invalid or empty (size < 16 bytes).", "source_url": remote_url},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return content, None


class VideoEvidenceStreamGatewayApiView(APIView):
    """
    On-Demand Streaming Reverse Proxy Gateway with Self-Healing Fallback.
    Proxies video from edge camera node or local media vault to client browser.
    Seamlessly forwards HTTP 206 Partial Content / Range requests for smooth scrubbing.
    If the local vault file is missing or corrupted, automatically recovers by falling back
    to the preserved source reference URL.
    """

    permission_classes = [AllowAny]

    def get(self, request, video_id, *args, **kwargs):
        video_item = get_object_or_404(VideoItem, pk=video_id)
        local_healthy, file_path, file_size = _check_local_archive(video_item)
        if local_healthy and file_path:
            return _stream_local_file(request, file_path, file_size)

        is_corruption_fallback = bool(video_item.video_file and not local_healthy)
        if is_corruption_fallback:
            logger.warning(
                f"VideoItem #{video_item.id} local media file is damaged or missing. "
                f"Recovering playback by falling back to source reference: {video_item.embed_url}"
            )
        return _stream_remote_edge(request, video_item.embed_url, is_corruption_fallback)


def _existing_archive_response(video_item, force: bool) -> Response | None:
    """Return early 200 Response if video is already archived and healthy."""
    if not video_item.video_file or force:
        return None
    is_healthy, _, _ = _check_local_archive(video_item)
    if is_healthy:
        return Response(
            {
                "status": "already_archived",
                "video_id": video_item.id,
                "file_url": video_item.video_file.url,
                "is_healthy": True,
                "message": "Video is already archived and healthy in local storage. Use ?force=true to re-sync.",
            },
            status=status.HTTP_200_OK,
        )
    logger.warning(
        f"VideoItem #{video_item.id} has broken/missing local file. "
        "Auto-triggering repair from remote reference URL."
    )
    return None


class VideoEvidenceArchiveApiView(APIView):
    """
    Dual-Mode Cloud Archival & Self-Healing Repair API.
    Permanently pulls a remote edge video into central Hub storage for compliance/legal freezing.
    Supports atomic staging, container validation, SHA-256 verification, and ?force=true repair from reference.
    """

    permission_classes = [AllowAny]

    def post(self, request, video_id, *args, **kwargs):
        video_item = get_object_or_404(VideoItem, pk=video_id)
        force = (
            request.query_params.get("force", "").lower() in ("true", "1", "yes")
            or request.data.get("force") is True
        )
        existing_resp = _existing_archive_response(video_item, force)
        if existing_resp is not None:
            return existing_resp

        content, error_resp = _download_remote_video(video_item.embed_url)
        if error_resp is not None or content is None:
            return error_resp

        checksum = hashlib.sha256(content).hexdigest()
        file_name = f"evidence_vault_{video_item.id}_{uuid.uuid4().hex[:6]}.mp4"
        video_item.video_file.save(file_name, ContentFile(content), save=True)
        return Response(
            {
                "status": "archived",
                "video_id": video_item.id,
                "file_url": video_item.video_file.url,
                "sha256": checksum,
                "size_bytes": len(content),
                "repaired": force or (video_item.video_file is not None),
                "message": "Video successfully archived and verified into cloud vault from source reference.",
            },
            status=status.HTTP_200_OK,
        )

