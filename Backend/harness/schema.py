from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

class SourceType(str, Enum):
    SENSOR = "sensor"
    FEED = "feed"
    CITIZEN = "citizen"
    FORECAST = "forecast"
    OFFICIAL = "official"

class LayerEnum(str, Enum):
    WX = "WX"
    HYD = "HYD"
    TRF = "TRF"
    PWR = "PWR"
    EMS = "EMS"
    HOS = "HOS"
    HLT = "HLT"
    AIR = "AIR"
    SEI = "SEI"
    COM = "COM"

class RiskState(str, Enum):
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"

class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"

class CanonicalEvent(BaseModel):
    event_id: str = Field(..., description="Idempotency key; duplicates dropped")
    source_id: str = Field(..., description="Unique source identifier")
    source_type: SourceType = Field(..., description="Source classification")
    layer: LayerEnum = Field(..., description="Urban infrastructure layer")
    zone_id: str = Field(..., description="Spatial zone identifier or H3 cell")
    variable: str = Field(..., description="Measured or forecasted variable name")
    value: float = Field(..., description="Standardized SI or index value")
    event_time: datetime = Field(..., description="Timestamp of physical occurrence (UTC)")
    ingest_time: datetime = Field(..., description="Timestamp when system first received event (UTC)")
    issued_at: Optional[datetime] = Field(None, description="Issuance timestamp for forecasts")
    valid_for: Optional[datetime] = Field(None, description="Target forecast validity timestamp")
    quality: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Declared data quality")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary")

class IngestBatchRequest(BaseModel):
    events: List[CanonicalEvent]

class IngestBatchResponse(BaseModel):
    accepted: int
    duplicates: int
    rejected: List[Dict[str, str]]
    watermark: str

class CityRiskSummary(BaseModel):
    state: RiskState
    p_cascade_24h: float
    rho: float
    confidence: ConfidenceLevel

class ExposureSummary(BaseModel):
    population_est: int
    assets: List[str]
    provenance: str = "MODELLED"

class ZoneRiskRecord(BaseModel):
    zone_id: str
    state: RiskState
    confidence: ConfidenceLevel
    evidence_coverage: float
    p: Dict[str, float]  # horizons: "1", "3", "6", "12", "24", "48", "72"
    t_critical: Dict[str, Optional[float]]  # q10, q50, q90, beyond_72h_p
    event_types: Dict[str, Dict[str, float]]
    exposure: ExposureSummary

class RiskResponse(BaseModel):
    as_of: str
    scenario: str
    fault_profile: str
    city: CityRiskSummary
    zones: List[ZoneRiskRecord]

class CascadeStage(BaseModel):
    layer: str
    event: str
    eta_h: Dict[str, float]  # q10, q50, q90
    affected_zones: List[str] = Field(default_factory=list)

class CascadeChain(BaseModel):
    rank: int
    prob: float
    stages: List[CascadeStage]

class BranchPoint(BaseModel):
    at: str
    to: str
    prob: float

class FeedbackLoop(BaseModel):
    nodes: List[str]
    gain: float

class CascadeResponse(BaseModel):
    chains: List[CascadeChain]
    branches: List[BranchPoint]
    rho: float
    loops: List[FeedbackLoop]
    interaction_gain: Optional[float] = None
    low_confidence: bool = False

class EdgeEvidenceCard(BaseModel):
    from_layer: str = Field(..., alias="from")
    to_layer: str = Field(..., alias="to")
    weight: float
    lag_peak_h: int
    ci: Tuple[float, float]
    lr_p: float
    precedes_count: int
    shuffled_baseline: int
    mechanism: str
    unsupported_flag: bool
    history: List[Dict[str, Any]]

    class Config:
        populate_by_name = True

class InterventionOption(BaseModel):
    id: str
    name: str
    dP: Dict[str, float]  # horizon: delta_P
    d_eta: Dict[str, float]
    d_rho: float
    side_effects: List[Dict[str, Any]]
    cost: float
    resources: Dict[str, int]
    deadline_h: float
    sensitivity_band: Tuple[float, float]

class InterveneResponse(BaseModel):
    baseline: Dict[str, Any]
    plans: List[InterventionOption]

class SourceReliability(BaseModel):
    source_id: str
    source_type: str
    layer: str
    reliability: float
    staleness_h: float
    quarantined: bool
    history: List[float]

class SourcesResponse(BaseModel):
    sources: List[SourceReliability]
    quarantined_clusters: List[Dict[str, Any]]

class LedgerRecord(BaseModel):
    forecast_id: str
    as_of: str
    data_max_ingest_time: str
    input_digest: str
    model_version: str
    outputs: Dict[str, Any]
    prev_hash: str
    hash: str

class LedgerVerifyResponse(BaseModel):
    ok: bool
    n_records: int
    first_bad: Optional[str]
    canary_passed: bool
