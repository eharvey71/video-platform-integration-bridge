from config import app
from flask import json, request, abort, jsonify
from src.models import ZoomClientConfig
import src.logger as logger
import requests
from requests.exceptions import HTTPError
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
import re


class ZoomOAuth:
    TOKEN_URL = "https://zoom.us/oauth/token"

    def __init__(self):
        self.config = self.get_config()
        self.access_token = None
        self.token_expiry = None

    @staticmethod
    def get_config():
        return ZoomClientConfig.query.first()

    def get_access_token(self):
        if (
            self.access_token
            and self.token_expiry
            and datetime.now() < self.token_expiry
        ):
            return self.access_token

        config = self.get_config()
        if not config:
            raise ValueError("Zoom client configuration not found in the database")

        data = {
            "grant_type": "account_credentials",
            "account_id": config.zoom_account_id,
            "client_id": config.zoom_client_id,
            "client_secret": config.zoom_client_secret,
        }

        try:
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data["access_token"]
            self.token_expiry = datetime.now() + timedelta(
                seconds=token_data["expires_in"]
            )

            return self.access_token
        except HTTPError as http_err:
            if response.status_code == 400:
                error_message = "Failed to obtain Zoom access token. Please check your Zoom credentials."
                logger.log(f"{error_message} Details: {response.text}")
                raise ValueError(error_message) from http_err
            raise


class ZoomClient:
    BASE_URL = "https://api.zoom.us/v2"

    def __init__(self):
        self.oauth = ZoomOAuth()

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.oauth.get_access_token()}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> Dict:
        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.request(
            method, url, headers=self._get_headers(), params=params, json=data
        )
        response.raise_for_status()
        return response.json()


def get_zoom_client():
    try:
        with app.app_context():
            zoom_config = ZoomClientConfig.query.get(1)
            if not zoom_config:
                raise ValueError("Zoom client configuration not found")
        return ZoomClient()
    except Exception as e:
        logger.log(f"Error creating ZoomClient: {str(e)}")
        raise


def validate_access_key(apikey, required_scopes=None, request=None):
    with app.app_context():
        zoom_config = ZoomClientConfig.query.get(1)
        if zoom_config and zoom_config.require_access_key:
            if apikey and apikey == zoom_config.access_key:
                return {"sub": "zoom_api_user"}
    return None


def verify_access_key():
    with app.app_context():
        zoom_config = ZoomClientConfig.query.get(1)
        if zoom_config and zoom_config.require_access_key:
            access_key = request.headers.get("X-Access-Key")
            if not validate_access_key(access_key):
                abort(401, description="Invalid or missing Access Key")


def get_meeting_recordings(meeting_id: str) -> Dict:
    """
    Retrieve the recordings for a specific meeting.
    """
    try:
        verify_access_key()
        client = get_zoom_client()

        recordings = client._make_request("GET", f"meetings/{meeting_id}/recordings")
        return recordings

    except Exception as e:
        logger.log(f"Error retrieving meeting recordings: {str(e)}")
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500


def get_meeting_transcript(meeting_id: str) -> Dict:
    """
    Retrieve the transcript for a specific meeting.
    """
    try:
        verify_access_key()
        client = get_zoom_client()
        recordings = get_meeting_recordings(meeting_id)
        recording_files = recordings.get("recording_files", [])

        transcript_file = next(
            (file for file in recording_files if file.get("file_type") == "TRANSCRIPT"),
            None,
        )
        if not transcript_file:
            return {"transcript": None, "message": "No transcript found"}

        transcript_url = transcript_file.get("download_url")
        if not transcript_url:
            return {"transcript": None, "message": "No transcript URL available"}

        transcript_content = get_transcript_content(
            transcript_url, client.oauth.get_access_token()
        )
        if not transcript_content:
            return {
                "transcript": None,
                "message": "Failed to retrieve transcript content",
            }

        return {"transcript": json.loads(webvtt_to_json(transcript_content))}

    except Exception as e:
        logger.log(f"Error retrieving meeting transcript: {str(e)}")
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500


def get_instructor_recordings(instructor_id: str, course_id: str = None) -> Dict:
    """
    Retrieve all recordings for an instructor filtered by course ID using meeting reports.
    The instructor_id parameter can be either an email or login ID from the LTI launch.
    """
    try:
        verify_access_key()
        client = get_zoom_client()
        logger.log(
            f"Starting recording search for instructor: {instructor_id}"
            + (
                f" with course filter: {course_id}"
                if course_id
                else " (no course filter)"
            )
        )

        start_date = datetime(2020, 1, 1)
        end_date = datetime.now()

        all_recordings = []
        current_date = end_date

        while current_date >= start_date:
            range_end = current_date.strftime("%Y-%m-%d")
            range_start = (current_date - timedelta(days=30)).strftime("%Y-%m-%d")

            try:
                recordings_response = client._make_request(
                    "GET",
                    f"users/{instructor_id}/recordings",
                    params={"page_size": 300, "from": range_start, "to": range_end},
                )

                recordings = recordings_response.get("meetings", [])
                # logger.log(
                #    f"Found {len(recordings)} recordings for date range {range_start} to {range_end}"
                # )
                all_recordings.extend(recordings)

            except HTTPError as e:
                if e.response.status_code == 404:
                    try:
                        user = client._make_request("GET", f"users/{instructor_id}")
                        user_id = user.get("id")
                        logger.log(f"Retrying with resolved user ID: {user_id}")

                        recordings_response = client._make_request(
                            "GET",
                            f"users/{user_id}/recordings",
                            params={
                                "page_size": 300,
                                "from": range_start,
                                "to": range_end,
                            },
                        )

                        recordings = recordings_response.get("meetings", [])
                        logger.log(
                            f"Found {len(recordings)} recordings using resolved user ID"
                        )
                        all_recordings.extend(recordings)

                    except HTTPError:
                        logger.log(
                            f"No Zoom user found for identifier: {instructor_id}"
                        )
                        return {"recordings": [], "message": "No Zoom user found"}
                else:
                    raise

            current_date = current_date - timedelta(days=30)

        logger.log(f"Total recordings found before filtering: {len(all_recordings)}")

        filtered_recordings = []
        for recording in all_recordings:
            meeting_id = recording.get("id")
            uuid = recording.get("uuid", "")
            topic = recording.get("topic", "No topic")

            try:
                meeting_report = client._make_request(
                    "GET", f"report/meetings/{meeting_id}"
                )
                logger.log(f"Checking meeting ID: {meeting_id} - Topic: {topic}")

            except HTTPError as meeting_error:
                error_response = json.loads(meeting_error.response.text)
                if (
                    meeting_error.response.status_code == 404
                    and error_response.get("code") == 3001
                ):
                    try:
                        logger.log(f"Retrying meeting {meeting_id} with UUID: {uuid}")
                        meeting_report = client._make_request(
                            "GET", f"report/meetings/{uuid}"
                        )
                    except HTTPError:
                        logger.log(
                            f"Failed to get report for meeting {meeting_id} using both ID and UUID"
                        )
                        continue
                else:
                    logger.log(f"Failed to get report for meeting {meeting_id}")
                    continue

            # If no course_id specified, include all recordings
            if not course_id:
                logger.log(f"Including meeting {meeting_id} (no course filter)")
                recording_info = {
                    "id": recording.get("id"),
                    "uuid": recording.get("uuid"),
                    "topic": recording.get("topic"),
                    "start_time": recording.get("start_time"),
                    "duration": recording.get("duration"),
                    "recording_files": [
                        {
                            "id": f.get("id"),
                            "file_type": f.get("file_type"),
                            "recording_type": f.get("recording_type"),
                            "download_url": f.get("download_url"),
                        }
                        for f in recording.get("recording_files", [])
                        if f.get("file_type") in ["MP4", "TRANSCRIPT"]
                    ],
                }
                filtered_recordings.append(recording_info)
            else:
                # Check course ID match
                tracking_fields = meeting_report.get("tracking_fields", [])
                canvas_course_field = next(
                    (
                        field
                        for field in tracking_fields
                        if field.get("field") == "Canvas Course"
                    ),
                    None,
                )

                if canvas_course_field and str(
                    canvas_course_field.get("value", "")
                ) == str(course_id):
                    logger.log(
                        f"Found matching course ID {course_id} for meeting {meeting_id}"
                    )
                    recording_info = {
                        "id": recording.get("id"),
                        "uuid": recording.get("uuid"),
                        "topic": recording.get("topic"),
                        "start_time": recording.get("start_time"),
                        "duration": recording.get("duration"),
                        "recording_files": [
                            {
                                "id": f.get("id"),
                                "file_type": f.get("file_type"),
                                "recording_type": f.get("recording_type"),
                                "download_url": f.get("download_url"),
                            }
                            for f in recording.get("recording_files", [])
                            if f.get("file_type") in ["MP4", "TRANSCRIPT"]
                        ],
                    }
                    filtered_recordings.append(recording_info)
                else:
                    logger.log(f"No matching course ID for meeting {meeting_id}")

        logger.log(
            f"Found {len(filtered_recordings)} recordings"
            + (f" matching course ID {course_id}" if course_id else " for instructor")
        )
        return {"recordings": filtered_recordings}

    except Exception as e:
        logger.log(f"Error retrieving instructor recordings: {str(e)}")
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500


def get_recording_transcript(recording_id: str) -> Dict:
    """
    Get transcript for a specific recording.
    """
    try:
        verify_access_key()
        client = get_zoom_client()

        try:
            recording = client._make_request("GET", f"recordings/{recording_id}")

            transcript_file = next(
                (
                    file
                    for file in recording.get("recording_files", [])
                    if file.get("file_type") == "TRANSCRIPT"
                ),
                None,
            )

            if not transcript_file:
                return {"transcript": None, "message": "No transcript available"}

            transcript_content = get_transcript_content(
                transcript_file["download_url"], client.oauth.get_access_token()
            )

            if not transcript_content:
                return {"transcript": None, "message": "Failed to retrieve transcript"}

            return {"transcript": json.loads(webvtt_to_json(transcript_content))}

        except HTTPError as e:
            if e.response.status_code == 404:
                return {"transcript": None, "message": "Recording not found"}
            raise

    except Exception as e:
        logger.log(f"Error retrieving recording transcript: {str(e)}")
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500


def get_transcript_content(
    transcript_download_url: str, access_token: str
) -> Optional[str]:
    """Download and return the content of the transcript file."""
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(transcript_download_url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.log(f"Error retrieving transcript: {str(e)}")
        return None


def webvtt_to_json(webvtt_content: str) -> str:
    """Convert WebVTT format to JSON."""
    captions = re.split(r"\r\n\r\n", webvtt_content.strip())

    json_data = []

    for caption in captions:
        if caption.strip().upper() == "WEBVTT":
            continue

        lines = caption.split("\r\n")
        if len(lines) >= 3:
            index = lines[0]
            timing = lines[1]
            text = " ".join(lines[2:])

            try:
                start, end = timing.split(" --> ")
            except ValueError:
                continue

            caption_obj = {"index": index, "start": start, "end": end, "text": text}

            json_data.append(caption_obj)

    return json.dumps(json_data)
