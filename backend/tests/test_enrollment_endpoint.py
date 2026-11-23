import io
import asyncio

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from backend.app.api.v1.endpoints.enrollment import enroll_subject
from backend.app.api.v1.endpoints import enrollment
from backend.app.face.recognition.exceptions import (
    FaceNotDetectedError,
    ModelUnavailableError,
)


def make_upload(filename: str = "face.jpg") -> UploadFile:
    return UploadFile(
        file=io.BytesIO(b"face-image"),
        filename=filename,
        headers=Headers({"content-type": "image/jpeg"}),
    )


def test_enrollment_requires_face_file(monkeypatch):
    monkeypatch.setattr(
        enrollment.enrollment_service,
        "enroll_subject",
        lambda **kwargs: pytest.fail("Enrollment service should not run"),
    )

    async def invoke():
        with pytest.raises(HTTPException) as exc:
            await enroll_subject(
                subject_id="person-a",
                consent_confirmed=True,
                face_image=None,
                voice_sample=None,
                session=object(),
            )
        return exc

    exc = asyncio.run(invoke())

    assert exc.value.status_code == 422
    assert exc.value.detail == "A face image is required for face enrollment"


def test_enrollment_maps_missing_face_to_422(monkeypatch):
    async def reject_face(**kwargs):
        raise FaceNotDetectedError()

    monkeypatch.setattr(
        enrollment.enrollment_service,
        "enroll_subject",
        reject_face,
    )

    async def invoke():
        with pytest.raises(HTTPException) as exc:
            await enroll_subject(
                subject_id="person-a",
                consent_confirmed=True,
                face_image=make_upload(),
                voice_sample=None,
                session=object(),
            )
        return exc

    exc = asyncio.run(invoke())

    assert exc.value.status_code == 422
    assert exc.value.detail == "No face detected in the provided image"


def test_enrollment_maps_model_unavailable_to_503(monkeypatch):
    async def unavailable_model(**kwargs):
        raise ModelUnavailableError()

    monkeypatch.setattr(
        enrollment.enrollment_service,
        "enroll_subject",
        unavailable_model,
    )

    async def invoke():
        with pytest.raises(HTTPException) as exc:
            await enroll_subject(
                subject_id="person-a",
                consent_confirmed=True,
                face_image=make_upload(),
                voice_sample=None,
                session=object(),
            )
        return exc

    exc = asyncio.run(invoke())

    assert exc.value.status_code == 503
