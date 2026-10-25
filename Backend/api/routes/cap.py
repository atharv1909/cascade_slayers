from __future__ import annotations
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict, Any

def generate_cap_alert_xml(
    alert_id: str,
    zone_id: str,
    zone_name: str,
    risk_state: str,
    headline: str,
    description: str,
    instruction: str,
    as_of: datetime
) -> str:
    """
    Generates OASIS Common Alerting Protocol (CAP) v1.2 XML document.
    Standard machine-readable emergency protocol used by civil protection authorities.
    """
    sent_str = as_of.isoformat()
    cap_ns = "urn:oasis:names:tc:emergency:cap:1.2"

    alert = ET.Element("alert", xmlns=cap_ns)
    ET.SubElement(alert, "identifier").text = f"AGY-72H-{alert_id}"
    ET.SubElement(alert, "sender").text = "early-warning@cascade-slayers.gov"
    ET.SubElement(alert, "sent").text = sent_str
    ET.SubElement(alert, "status").text = "Actual"
    ET.SubElement(alert, "msgType").text = "Alert"
    ET.SubElement(alert, "scope").text = "Public"

    info = ET.SubElement(alert, "info")
    ET.SubElement(info, "category").text = "Safety"
    ET.SubElement(info, "event").text = f"Cascading Infrastructure Failure - {risk_state}"
    
    urgency = "Immediate" if risk_state == "CRITICAL" else ("Expected" if risk_state == "HIGH_RISK" else "Future")
    severity = "Extreme" if risk_state == "CRITICAL" else ("Severe" if risk_state == "HIGH_RISK" else "Moderate")
    certainty = "Observed" if risk_state == "CRITICAL" else "Likely"

    ET.SubElement(info, "urgency").text = urgency
    ET.SubElement(info, "severity").text = severity
    ET.SubElement(info, "certainty").text = certainty
    ET.SubElement(info, "headline").text = headline
    ET.SubElement(info, "description").text = description
    ET.SubElement(info, "instruction").text = instruction

    area = ET.SubElement(info, "area")
    ET.SubElement(area, "areaDesc").text = f"{zone_name} ({zone_id})"
    ET.SubElement(area, "geocode").text = zone_id

    return ET.tostring(alert, encoding="utf-8", xml_declaration=True).decode("utf-8")
