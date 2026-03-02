from pydantic import BaseModel, Field


class BusinessCreate(BaseModel):
    business_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    summary: str | None = None
    rules_doc: str | None = None


class ResourceManifest(BaseModel):
    business_id: str
    db_name: str
    vector_namespace: str
    s3_path: str
    k8s_namespace: str
    secret_ref: str

