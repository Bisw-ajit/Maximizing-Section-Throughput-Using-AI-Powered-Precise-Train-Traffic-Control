from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from ..core.database import Base


class Train(Base):
    __tablename__ = "trains"

    train_id: Mapped[str] = mapped_column(String, primary_key=True)
    train_number: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=3)  # 1=highest, 5=lowest
    current_node: Mapped[str | None] = mapped_column(String, nullable=True)
    current_section: Mapped[str | None] = mapped_column(String, nullable=True)
    direction: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="SCHEDULED")
    delay_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    next_station: Mapped[str | None] = mapped_column(String, nullable=True)
    route_id: Mapped[str | None] = mapped_column(String, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    data_source: Mapped[str] = mapped_column(String, default="SCENARIO")
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    staleness_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    journey_progress: Mapped[float] = mapped_column(Float, default=0.0)


class Node(Base):
    __tablename__ = "nodes"

    node_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    node_type: Mapped[str] = mapped_column(String, nullable=False)  # STATION, JUNCTION
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)


class Section(Base):
    __tablename__ = "sections"

    section_id: Mapped[str] = mapped_column(String, primary_key=True)
    from_node: Mapped[str] = mapped_column(String, ForeignKey("nodes.node_id"))
    to_node: Mapped[str] = mapped_column(String, ForeignKey("nodes.node_id"))
    length_km: Mapped[float] = mapped_column(Float, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    allowed_movements: Mapped[str] = mapped_column(String, default="BOTH")
    is_bidirectional: Mapped[bool] = mapped_column(Boolean, default=True)


class SectionOccupancy(Base):
    __tablename__ = "section_occupancy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    section_id: Mapped[str] = mapped_column(String, ForeignKey("sections.section_id"))
    train_id: Mapped[str] = mapped_column(String, ForeignKey("trains.train_id"))
    entry_time: Mapped[datetime] = mapped_column(DateTime)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Conflict(Base):
    __tablename__ = "conflicts"

    conflict_id: Mapped[str] = mapped_column(String, primary_key=True)
    conflict_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    train_ids: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list
    predicted_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="PREDICTED")


class Recommendation(Base):
    __tablename__ = "recommendations"

    recommendation_id: Mapped[str] = mapped_column(String, primary_key=True)
    conflict_id: Mapped[str] = mapped_column(String, ForeignKey("conflicts.conflict_id"))
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    affected_trains: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list
    score: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expected_delay_change: Mapped[float] = mapped_column(Float, default=0.0)
    expected_waiting_change: Mapped[float] = mapped_column(Float, default=0.0)
    feasible: Mapped[bool] = mapped_column(Boolean, default=True)


class Scenario(Base):
    __tablename__ = "scenarios"

    scenario_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    network_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String, ForeignKey("scenarios.scenario_id"))
    strategy: Mapped[str] = mapped_column(String, default="BASELINE")
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    throughput: Mapped[int] = mapped_column(Integer, default=0)
    average_delay: Mapped[float] = mapped_column(Float, default=0.0)
    waiting_time: Mapped[float] = mapped_column(Float, default=0.0)
    conflict_count: Mapped[int] = mapped_column(Integer, default=0)
    utilization: Mapped[float] = mapped_column(Float, default=0.0)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(String, primary_key=True, default="local")
    favorite_trains: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    recent_searches: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    dashboard_preferences: Mapped[str] = mapped_column(Text, default="{}")  # JSON dict
