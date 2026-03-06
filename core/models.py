"""
Data models for the Productboard demo generator.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# Configurable caps for flexible hierarchy generation
DEFAULT_MAX_PRODUCTS = 2
DEFAULT_MAX_COMPONENTS_PER_PRODUCT = 10
DEFAULT_MAX_FEATURES_PER_COMPONENT = 20


class StepStatus(str, Enum):
    """Status of a job step."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of a single step in the job execution."""
    name: str
    status: StepStatus
    summary: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "summary": self.summary,
            "logs": self.logs,
            "error": self.error,
        }


@dataclass
class FlexibleOptions:
    """Options for flexible hierarchy generation."""
    max_components_per_product: int = DEFAULT_MAX_COMPONENTS_PER_PRODUCT
    max_features_per_component: int = DEFAULT_MAX_FEATURES_PER_COMPONENT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "maxComponentsPerProduct": self.max_components_per_product,
            "maxFeaturesPerComponent": self.max_features_per_component,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlexibleOptions":
        return cls(
            max_components_per_product=data.get("maxComponentsPerProduct", DEFAULT_MAX_COMPONENTS_PER_PRODUCT),
            max_features_per_component=data.get("maxFeaturesPerComponent", DEFAULT_MAX_FEATURES_PER_COMPONENT),
        )


@dataclass
class ProductInfo:
    """Information about a Productboard product."""
    id: str
    name: str
    component_count: int
    feature_count: int = 0
    eligible: bool = True
    ineligible_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "componentCount": self.component_count,
            "featureCount": self.feature_count,
            "eligible": self.eligible,
            "ineligibleReason": self.ineligible_reason,
        }


@dataclass
class SelectedProduct:
    """A product selected for the POC."""
    id: str
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name}


@dataclass
class JobResult:
    """Complete result of a POC job execution."""
    job_id: str
    mode: str  # 'dry-run' or 'apply'
    company: str
    website: str
    selected_products: List[SelectedProduct]
    steps: List[StepResult]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "jobId": self.job_id,
            "mode": self.mode,
            "company": self.company,
            "website": self.website,
            "selectedProducts": [p.to_dict() for p in self.selected_products],
            "steps": [s.to_dict() for s in self.steps],
            "warnings": self.warnings,
            "errors": self.errors,
            "completedAt": self.completed_at,
        }


@dataclass
class FeatureMapping:
    """Mapping for a single feature."""
    position: int
    new_name: str


@dataclass
class ComponentMapping:
    """Mapping for a component and its features."""
    position: int
    new_name: str
    features: List[FeatureMapping]


@dataclass
class ProductHierarchyMapping:
    """Mapping for a product and its components."""
    position: int
    new_name: str
    components: List[ComponentMapping]


@dataclass
class ProductMapping:
    """Complete product hierarchy mapping."""
    customer: str
    hierarchy: List[ProductHierarchyMapping]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer": self.customer,
            "hierarchy": [
                {
                    "position": p.position,
                    "newName": p.new_name,
                    "components": [
                        {
                            "position": c.position,
                            "newName": c.new_name,
                            "features": [
                                {"position": f.position, "newName": f.new_name}
                                for f in c.features
                            ],
                        }
                        for c in p.components
                    ],
                }
                for p in self.hierarchy
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductMapping":
        """Create ProductMapping from dictionary."""
        hierarchy = []
        for p in data.get("hierarchy", []):
            components = []
            for c in p.get("components", []):
                features = [
                    FeatureMapping(position=f["position"], new_name=f["newName"])
                    for f in c.get("features", [])
                ]
                components.append(
                    ComponentMapping(
                        position=c["position"],
                        new_name=c["newName"],
                        features=features,
                    )
                )
            hierarchy.append(
                ProductHierarchyMapping(
                    position=p["position"],
                    new_name=p["newName"],
                    components=components,
                )
            )
        return cls(customer=data.get("customer", ""), hierarchy=hierarchy)


@dataclass
class KeyResultMapping:
    """Mapping for a key result."""
    position: int
    new_name: str


@dataclass
class ObjectiveMapping:
    """Mapping for an objective and its key results."""
    position: int
    new_name: str
    key_results: List[KeyResultMapping]


@dataclass
class InitiativeMapping:
    """Mapping for an initiative."""
    position: int
    new_name: str


@dataclass
class StrategyMapping:
    """Complete strategy hierarchy mapping."""
    customer: str
    objectives: List[ObjectiveMapping]
    initiatives: List[InitiativeMapping]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer": self.customer,
            "objectives": [
                {
                    "position": o.position,
                    "newName": o.new_name,
                    "keyResults": [
                        {"position": kr.position, "newName": kr.new_name}
                        for kr in o.key_results
                    ],
                }
                for o in self.objectives
            ],
            "initiatives": [
                {"position": i.position, "newName": i.new_name}
                for i in self.initiatives
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyMapping":
        """Create StrategyMapping from dictionary."""
        objectives = []
        for o in data.get("objectives", []):
            key_results = [
                KeyResultMapping(position=kr["position"], new_name=kr["newName"])
                for kr in o.get("keyResults", [])
            ]
            objectives.append(
                ObjectiveMapping(
                    position=o["position"],
                    new_name=o["newName"],
                    key_results=key_results,
                )
            )
        initiatives = [
            InitiativeMapping(position=i["position"], new_name=i["newName"])
            for i in data.get("initiatives", [])
        ]
        return cls(
            customer=data.get("customer", ""),
            objectives=objectives,
            initiatives=initiatives,
        )


@dataclass
class ValidationError:
    """A validation error."""
    field: str
    message: str


@dataclass
class ValidationResult:
    """Result of validation."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [{"field": e.field, "message": e.message} for e in self.errors],
            "warnings": self.warnings,
        }


@dataclass
class ComponentStructure:
    """Structure info for a component in a product."""
    id: str
    name: str
    feature_count: int
    features: List[Dict[str, str]] = field(default_factory=list)  # [{id, name}]


@dataclass
class ProductStructure:
    """Complete structure info for a selected product."""
    id: str
    name: str
    components: List[ComponentStructure] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "components": [
                {
                    "id": c.id,
                    "name": c.name,
                    "featureCount": c.feature_count,
                    "features": c.features,
                }
                for c in self.components
            ],
        }


@dataclass
class AnalyzeResult:
    """Result of analyzing a Productboard space."""
    products: List[ProductInfo]
    warnings: List[str] = field(default_factory=list)
    auto_select_product_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "products": [p.to_dict() for p in self.products],
            "warnings": self.warnings,
            "recommendations": {
                "autoSelectProductIds": self.auto_select_product_ids,
            },
        }


@dataclass
class RenamePlan:
    """Plan for renaming entities - used for preview."""
    products: List[Dict[str, Any]] = field(default_factory=list)
    # Each product: {id, currentName, newName, components: [{id, currentName, newName, features: [...]}]}

    def to_dict(self) -> Dict[str, Any]:
        return {"products": self.products}
