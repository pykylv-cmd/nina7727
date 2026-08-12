"""Canonical runtime capability truth for ONE NINA.

The registry describes currently implemented shared capabilities. Channel
adapters must not override it or claim capabilities that the runtime cannot use.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
from typing import Mapping


class CapabilityId(str, Enum):
    BUSINESS_THINKING = "BUSINESS_THINKING"
    WEB_RESEARCH = "WEB_RESEARCH"
    WEBSITE_READER = "WEBSITE_READER"
    REMINDERS = "REMINDERS"
    TASKS = "TASKS"
    WORK_OBJECTS = "WORK_OBJECTS"
    MEMORY = "MEMORY"
    FILE_ANALYSIS = "FILE_ANALYSIS"
    IMAGE_UNDERSTANDING = "IMAGE_UNDERSTANDING"
    AUDIO_UNDERSTANDING = "AUDIO_UNDERSTANDING"
    VIDEO_UNDERSTANDING = "VIDEO_UNDERSTANDING"
    EMAIL_READ = "EMAIL_READ"
    EMAIL_DRAFT = "EMAIL_DRAFT"
    EMAIL_SEND = "EMAIL_SEND"
    CALENDAR_READ = "CALENDAR_READ"
    CALENDAR_WRITE = "CALENDAR_WRITE"
    CONTACTS = "CONTACTS"
    WEB_GUIDE = "WEB_GUIDE"
    AUTOMATION_DESIGN = "AUTOMATION_DESIGN"
    AUTOMATION_EXECUTION = "AUTOMATION_EXECUTION"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    DOCUMENT_GENERATION = "DOCUMENT_GENERATION"


class CapabilityState(str, Enum):
    AVAILABLE = "AVAILABLE"
    AVAILABLE_WITH_APPROVAL = "AVAILABLE_WITH_APPROVAL"
    REQUIRES_CONNECTION = "REQUIRES_CONNECTION"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True)
class CapabilityDescriptor:
    id: CapabilityId
    state: CapabilityState
    what_nina_can_do: str
    required_connection: str = ""
    approval_required: bool = False
    limitations: str = ""
    safe_user_description: str = ""


def _connected(env: Mapping[str, str], *keys: str) -> bool:
    return any(str(env.get(key, "")).strip().lower() in {"1", "true", "connected", "ready"} for key in keys)


def get_capability_registry(environment: Mapping[str, str] | None = None) -> dict[CapabilityId, CapabilityDescriptor]:
    env = environment if environment is not None else os.environ
    email_connected = _connected(env, "NINA_EMAIL_CONNECTED", "EMAIL_CONNECTED")
    calendar_connected = _connected(env, "NINA_CALENDAR_CONNECTED", "CALENDAR_CONNECTED")
    available = CapabilityState.AVAILABLE
    registry = {
        CapabilityId.BUSINESS_THINKING: CapabilityDescriptor(CapabilityId.BUSINESS_THINKING, available, "Analyze business decisions", safe_user_description="analizēt biznesa lēmumus un nākamo labāko soli"),
        CapabilityId.WEB_RESEARCH: CapabilityDescriptor(CapabilityId.WEB_RESEARCH, available, "Research verified public sources", limitations="Only verified public evidence", safe_user_description="izpētīt tirgu, konkurentus un publiskus avotus"),
        CapabilityId.WEBSITE_READER: CapabilityDescriptor(CapabilityId.WEBSITE_READER, available, "Read a supplied public website", limitations="Public safe URLs only", safe_user_description="izlasīt un analizēt drošu publisku tīmekļa lapu"),
        CapabilityId.REMINDERS: CapabilityDescriptor(CapabilityId.REMINDERS, available, "Create, list, update and deliver reminders", safe_user_description="uzturēt un piegādāt atgādinājumus"),
        CapabilityId.TASKS: CapabilityDescriptor(CapabilityId.TASKS, available, "Create and manage canonical tasks", safe_user_description="izveidot un pārvaldīt uzdevumus"),
        CapabilityId.WORK_OBJECTS: CapabilityDescriptor(CapabilityId.WORK_OBJECTS, available, "Structure durable work and projects", safe_user_description="strukturēt darbu un projektus vienā darba patiesībā"),
        CapabilityId.MEMORY: CapabilityDescriptor(CapabilityId.MEMORY, available, "Use scoped conversation and approved memory", limitations="Workspace/contact scoped", safe_user_description="turpināt darbu ar kopīgu, izolētu kontekstu"),
        CapabilityId.FILE_ANALYSIS: CapabilityDescriptor(CapabilityId.FILE_ANALYSIS, available, "Analyze supported files and documents", safe_user_description="analizēt failus un dokumentus"),
        CapabilityId.IMAGE_UNDERSTANDING: CapabilityDescriptor(CapabilityId.IMAGE_UNDERSTANDING, available, "Understand images and screenshots", safe_user_description="saprast attēlus un ekrānuzņēmumus"),
        CapabilityId.AUDIO_UNDERSTANDING: CapabilityDescriptor(CapabilityId.AUDIO_UNDERSTANDING, available, "Transcribe and understand audio", safe_user_description="saprast audio"),
        CapabilityId.VIDEO_UNDERSTANDING: CapabilityDescriptor(CapabilityId.VIDEO_UNDERSTANDING, available, "Analyze supported video", limitations="Subject to media limits", safe_user_description="analizēt atbalstītu video"),
        CapabilityId.EMAIL_DRAFT: CapabilityDescriptor(CapabilityId.EMAIL_DRAFT, available, "Prepare email drafts", limitations="Does not send without a connected sender", safe_user_description="sagatavot e-pasta atbildes melnrakstu"),
        CapabilityId.EMAIL_READ: CapabilityDescriptor(CapabilityId.EMAIL_READ, available if email_connected else CapabilityState.REQUIRES_CONNECTION, "Read connected email", required_connection="email", limitations="No inbox access until connected", safe_user_description="lasīt pieslēgtu e-pastu"),
        CapabilityId.EMAIL_SEND: CapabilityDescriptor(CapabilityId.EMAIL_SEND, CapabilityState.AVAILABLE_WITH_APPROVAL if email_connected else CapabilityState.REQUIRES_CONNECTION, "Send through a connected email account after approval", required_connection="email", approval_required=True, limitations="Cannot send before connection and approval", safe_user_description="nosūtīt apstiprinātu e-pastu pēc konta pieslēgšanas"),
        CapabilityId.CALENDAR_READ: CapabilityDescriptor(CapabilityId.CALENDAR_READ, available if calendar_connected else CapabilityState.REQUIRES_CONNECTION, "Read a connected calendar", required_connection="calendar", safe_user_description="lasīt pieslēgtu kalendāru"),
        CapabilityId.CALENDAR_WRITE: CapabilityDescriptor(CapabilityId.CALENDAR_WRITE, CapabilityState.AVAILABLE_WITH_APPROVAL if calendar_connected else CapabilityState.REQUIRES_CONNECTION, "Write to a connected calendar after approval", required_connection="calendar", approval_required=True, safe_user_description="ierakstīt apstiprinātu notikumu pieslēgtā kalendārā"),
        CapabilityId.CONTACTS: CapabilityDescriptor(CapabilityId.CONTACTS, available, "Use canonical workspace contacts", safe_user_description="strādāt ar canonical klientu un kontaktu kontekstu"),
        CapabilityId.WEB_GUIDE: CapabilityDescriptor(CapabilityId.WEB_GUIDE, available, "Guide the user through NinaOS", safe_user_description="izskaidrot un vadīt darbu NinaOS"),
        CapabilityId.AUTOMATION_DESIGN: CapabilityDescriptor(CapabilityId.AUTOMATION_DESIGN, available, "Design a safe automation proposal", safe_user_description="izstrādāt automatizācijas plānu"),
        CapabilityId.AUTOMATION_EXECUTION: CapabilityDescriptor(CapabilityId.AUTOMATION_EXECUTION, CapabilityState.NOT_IMPLEMENTED, "External automation execution is not generally available", approval_required=True, limitations="V1 can design and structure, not activate arbitrary external automation", safe_user_description="patvaļīga ārēja automatizācijas izpilde vēl nav pieejama"),
        CapabilityId.DATA_ANALYSIS: CapabilityDescriptor(CapabilityId.DATA_ANALYSIS, available, "Analyze supplied structured data", safe_user_description="analizēt iesniegtus datus"),
        CapabilityId.DOCUMENT_GENERATION: CapabilityDescriptor(CapabilityId.DOCUMENT_GENERATION, available, "Prepare document content and supported documents", safe_user_description="sagatavot dokumentus un to saturu"),
    }
    return registry


def capability(id: CapabilityId, environment: Mapping[str, str] | None = None) -> CapabilityDescriptor:
    return get_capability_registry(environment)[id]
