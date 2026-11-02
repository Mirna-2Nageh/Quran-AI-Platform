
"""Authenticated Halaqat management endpoints."""

from fastapi import APIRouter, Depends, Query, Request

from app.schemas.halaqat import (
    AttendanceRecordCreate,
    AttendanceRecordResponse,
    EnrollmentCreate,
    EnrollmentResponse,
    HalaqaCreate,
    HalaqaResponse,
    HalaqaSessionCreate,
    HalaqaSessionResponse,
)
from app.security.authorization import (
    current_user,
    current_user_write,
    require_roles,
)
from app.services.halaqat import HalaqatService

router = APIRouter(prefix="/halaqat", tags=["Halaqat"])


def serialize_halaqa(document):
    return {
        "id": str(document["_id"]),
        "name": document["name"],
        "description": document["description"],
        "teacher_id": str(document["teacher_id"]),
        "status": document["status"],
        "created_at": document["created_at"],
        "updated_at": document["updated_at"],
    }


def serialize_enrollment(document):
    return {
        "id": str(document["_id"]),
        "halaqa_id": str(document["halaqa_id"]),
        "student_id": str(document["student_id"]),
        "student_name": document.get("student_name"),
        "halaqa_name": document.get("halaqa_name"),
        "status": document["status"],
        "created_at": document["created_at"],
    }



def serialize_session(document):
    return {
        "id": str(document["_id"]),
        "halaqa_id": str(document["halaqa_id"]),
        "scheduled_at": document["scheduled_at"],
        "duration_minutes": document["duration_minutes"],
        "notes": document["notes"],
        "status": document["status"],
        "created_at": document["created_at"],
        "updated_at": document["updated_at"],
    }


def get_service(request: Request):
    return HalaqatService(request.app.state.database)


@router.get("", response_model=list[HalaqaResponse])
async def list_all_halaqat(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: HalaqatService = Depends(get_service),
    actor=Depends(require_roles("admin")),
):
    documents = await service.repository.list_all_halaqat(
        limit=limit,
        offset=offset,
    )
    return [serialize_halaqa(item) for item in documents]


@router.post("", response_model=HalaqaResponse, status_code=201)
async def create_halaqa(
    payload: HalaqaCreate,
    service: HalaqatService = Depends(get_service),
    actor=Depends(current_user_write),
):
    document = await service.create_halaqa(
        actor=actor,
        name=payload.name,
        description=payload.description,
        teacher_id=payload.teacher_id,
    )
    return serialize_halaqa(document)



@router.get(
    "/my/attendance",
    response_model=list[AttendanceRecordResponse],
)
async def get_my_attendance(
    service: HalaqatService = Depends(get_service),
    actor=Depends(current_user),
):
    documents = await service.list_my_attendance(actor=actor)
    return [serialize_attendance(item) for item in documents]


@router.get("/my", response_model=list[HalaqaResponse])
async def my_halaqat(
    service: HalaqatService = Depends(get_service),
    actor=Depends(current_user),
):
    from fastapi import HTTPException

    if actor.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Teacher required")

    documents = await service.repository.list_teacher_halaqat(
        str(actor["_id"])
    )
    return [serialize_halaqa(item) for item in documents]



@router.get(
    "/my/enrollments",
    response_model=list[EnrollmentResponse],
)
async def my_enrollments(
    service: HalaqatService = Depends(get_service),
    actor=Depends(current_user),
):
    documents = await service.list_my_enrollments(actor=actor)
    return [serialize_enrollment(item) for item in documents]


@router.get("/{halaqa_id}", response_model=HalaqaResponse)
async def get_halaqa(
    halaqa_id: str,
    service: HalaqatService = Depends(get_service),
    actor=Depends(current_user),
):
    document = await service.get_managed_halaqa(
        actor=actor,
        halaqa_id=halaqa_id,
    )
    return serialize_halaqa(document)


@router.post(
    "/{halaqa_id}/enrollments",
    response_model=EnrollmentResponse,
    status_code=201,
)
async def enroll_student(
    halaqa_id: str,
    payload: EnrollmentCreate,
    service: HalaqatService = Depends(get_service),
    actor=Depends(current_user_write),
):
    document = await service.enroll_student(
        actor=actor,
        halaqa_id=halaqa_id,
        student_id=payload.student_id,
    )
    return serialize_enrollment(document)


@router.get(
    "/{halaqa_id}/enrollments",
    response_model=list[EnrollmentResponse],
)
async def list_enrollments(
    halaqa_id: str,
    service: HalaqatService = Depends(get_service),
    actor=Depends(current_user),
):
    documents = await service.list_enrollments(
        actor=actor,
        halaqa_id=halaqa_id,
    )
    return [serialize_enrollment(item) for item in documents]


@router.post(
    "/{halaqa_id}/sessions",
    response_model=HalaqaSessionResponse,
    status_code=201,
)
async def create_halaqa_session(
    halaqa_id: str,
    payload: HalaqaSessionCreate,
    service: HalaqatService = Depends(get_service),
    actor=Depends(current_user_write),
):
    document = await service.create_session(
        actor=actor,
        halaqa_id=halaqa_id,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        notes=payload.notes,
    )
    return serialize_session(document)


@router.get(
    "/{halaqa_id}/sessions",
    response_model=list[HalaqaSessionResponse],
)
async def list_halaqa_sessions(
    halaqa_id: str,
    service: HalaqatService = Depends(get_service),
    actor=Depends(current_user),
):
    documents = await service.list_sessions(
        actor=actor,
        halaqa_id=halaqa_id,
    )
    return [serialize_session(item) for item in documents]



def serialize_attendance(document):
    return {
        "id": str(document["_id"]),
        "session_id": str(document["session_id"]),
        "halaqa_name": document.get("halaqa_name"),
        "session_scheduled_at": document.get("session_scheduled_at"),
        "student_id": str(document["student_id"]),
        "status": document["status"],
        "notes": document.get("notes"),
        "recorded_by": str(document["recorded_by"]),
        "created_at": document["created_at"],
        "updated_at": document["updated_at"],
    }




@router.get(
    "/sessions/{session_id}/attendance",
    response_model=list[AttendanceRecordResponse],
)
async def get_halaqa_session_attendance(
    session_id: str,
    service: HalaqatService = Depends(get_service),
    actor=Depends(current_user),
):
    documents = await service.list_session_attendance(
        actor=actor,
        session_id=session_id,
    )
    return [serialize_attendance(item) for item in documents]


@router.put(
    "/sessions/{session_id}/attendance",
    response_model=AttendanceRecordResponse,
)
async def record_halaqa_attendance(
    session_id: str,
    payload: AttendanceRecordCreate,
    service: HalaqatService = Depends(get_service),
    actor=Depends(current_user_write),
):
    document = await service.record_attendance(
        actor=actor,
        session_id=session_id,
        student_id=payload.student_id,
        status=payload.status,
        notes=payload.notes,
    )
    return serialize_attendance(document)
