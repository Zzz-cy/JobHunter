from app.schemas import SchemaBase, ORMOut


class OverviewOut(ORMOut):
    job_count: int
    company_count: int
    skill_count: int
    industry_count: int
    city_count: int

