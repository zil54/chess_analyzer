# db/models.py
# backend/db/models.py
from sqlalchemy.orm import declarative_base, mapped_column
from sqlalchemy import Text, String, TIMESTAMP, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
import datetime



Base = declarative_base()

class SessionAnalysis(Base):
    __tablename__ = "session_analysis"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fen = mapped_column(Text, nullable=False)
    status = mapped_column(String, nullable=False, default="created")
    created_at = mapped_column(TIMESTAMP(timezone=True),default=lambda: datetime.datetime.now(datetime.UTC))
    updated_at = mapped_column(TIMESTAMP(timezone=True),default=lambda: datetime.datetime.now(datetime.UTC))


class AnalysisLines(Base):
    __tablename__ = "analysis_lines"

    session_id = mapped_column(UUID(as_uuid=True),
                               ForeignKey("session_analysis.id", ondelete="CASCADE"),
                               primary_key=True)
    depth = mapped_column(Integer, primary_key=True)
    multipv = mapped_column(Integer, primary_key=True)
    line = mapped_column(Text, nullable=False)
    updated_at = mapped_column(TIMESTAMP(timezone=True),default=lambda: datetime.datetime.now(datetime.UTC))