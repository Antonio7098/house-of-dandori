from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict


class CourseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    class_id: Optional[str] = None
    title: str
    instructor: Optional[str] = None
    location: Optional[str] = None
    course_type: Optional[str] = None
    cost: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    provided_materials: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    description: Optional[str] = None
    filename: Optional[str] = None
    pdf_url: Optional[str] = None


class CourseCreate(CourseBase):
    title: str = Field(..., min_length=1, max_length=255)


class CourseUpdate(BaseModel):
    class_id: Optional[str] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    instructor: Optional[str] = None
    location: Optional[str] = None
    course_type: Optional[str] = None
    cost: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    provided_materials: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    description: Optional[str] = None


class CourseResponse(CourseBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CourseListResponse(BaseModel):
    count: int
    page: int
    limit: int
    total_pages: int
    courses: List[CourseResponse]


class BulkCourseRequest(BaseModel):
    ids: List[int] = Field(..., min_length=1, max_length=100)

    @field_validator("ids")
    @classmethod
    def validate_ids(cls, v):
        if not all(isinstance(i, int) and i > 0 for i in v):
            raise ValueError("All IDs must be positive integers")
        return v


class BulkCourseResponse(BaseModel):
    courses: List[CourseResponse]


class SearchQuery(BaseModel):
    q: str = Field(..., min_length=1, max_length=500)
    page: int = Field(default=1, ge=1)
    n: int = Field(default=10, ge=1, le=100)


class SearchResult(BaseModel):
    results: List[CourseResponse]
    count: int
    page: int
    limit: int
    total_pages: int


class CourseFilter(BaseModel):
    search: str = ""
    location: str = ""
    course_type: str = ""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class ConfigResponse(BaseModel):
    environment: str
    vectorStoreProvider: str


class HealthResponse(BaseModel):
    status: str


class UploadResponse(BaseModel):
    id: int
    message: str
    data: Optional[Dict[str, Any]] = None


class BatchUploadResponse(BaseModel):
    total: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]


class IndexResponse(BaseModel):
    message: str
    count: int


class ErrorResponse(BaseModel):
    error: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
