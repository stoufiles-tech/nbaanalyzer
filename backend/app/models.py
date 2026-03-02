from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    espn_id = Column(String, unique=True, index=True)
    abbreviation = Column(String)
    display_name = Column(String)
    location = Column(String)
    nickname = Column(String)
    logo_url = Column(String)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    cached_at = Column(DateTime, default=datetime.utcnow)


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    espn_id = Column(String, unique=True, index=True)
    full_name = Column(String)
    position = Column(String)
    team_id = Column(String)
    team_abbr = Column(String)
    jersey = Column(String)
    salary = Column(Float, default=0.0)
    age = Column(Integer, default=0)
    # Per-game stats
    points = Column(Float, default=0.0)
    rebounds = Column(Float, default=0.0)
    assists = Column(Float, default=0.0)
    steals = Column(Float, default=0.0)
    blocks = Column(Float, default=0.0)
    field_goal_pct = Column(Float, default=0.0)
    three_point_pct = Column(Float, default=0.0)
    free_throw_pct = Column(Float, default=0.0)
    minutes = Column(Float, default=0.0)
    games_played = Column(Integer, default=0)
    # Derived metrics
    per = Column(Float, default=0.0)
    true_shooting_pct = Column(Float, default=0.0)
    value_score = Column(Float, default=0.0)
    cached_at = Column(DateTime, default=datetime.utcnow)


class CapData(Base):
    __tablename__ = "cap_data"

    id = Column(Integer, primary_key=True)
    season = Column(String)
    salary_cap = Column(Float)
    luxury_tax_threshold = Column(Float)
    apron = Column(Float)
    cached_at = Column(DateTime, default=datetime.utcnow)
