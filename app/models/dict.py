"""
字典表模型

对应数据库表:
    - skills       技能字典(与 Neo4j Skill 节点对应)
    - industries   行业/城市层级字典
"""
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPk, TimestampMixin


# ============================================================
# 技能字典
# ============================================================
class Skill(Base, TimestampMixin):
    """技能标准化字典。

    与 Neo4j 中的 Skill 节点一一对应, alias 用于规则匹配。
    字典表不做软删除
    """

    __tablename__ = "skills"

    id: Mapped[int] = BigIntPk()
    skill_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    alias: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    is_hot: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)

    # 反向关系
    # 供 JobSkill.skill 反向引用; 查"某技能被多少职位需要"时也用得到。
    job_skills: Mapped[list["JobSkill"]] = relationship(  # noqa: F821
        back_populates="skill",
    )

    def __repr__(self) -> str:
        return f"<Skill(id={self.id}, name={self.name!r}, category={self.category!r})>"


# 行业字典
class Industry(Base):
    """行业/城市层级字典

    纯字典表, 不带时间戳/软删除, 主键 INT(不是 BIGINT)。
    """

    __tablename__ = "industries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(Integer, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def __repr__(self) -> str:
        return f"<Industry(id={self.id}, code={self.code!r}, name={self.name!r})>"
