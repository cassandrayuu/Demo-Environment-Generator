"""
Productboard API Client

A unified wrapper around the Productboard API with:
- Retry logic with exponential backoff and jitter
- Structured error types
- Token passed per-request (never persisted)
"""

import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

# API endpoints - fully V2 (V1 deprecated July 8, 2026)
API_BASE = "https://api.productboard.com/v2"

# Retry configuration
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 32.0
JITTER_FACTOR = 0.1

# Request timeout
REQUEST_TIMEOUT = 30


class ProductboardError(Exception):
    """Base exception for Productboard API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class AuthError(ProductboardError):
    """Authentication or authorization error (401/403)."""

    pass


class RateLimitError(ProductboardError):
    """Rate limit exceeded (429)."""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message, 429)
        self.retry_after = retry_after


class NotFoundError(ProductboardError):
    """Resource not found (404)."""

    pass


class ServerError(ProductboardError):
    """Server error (5xx)."""

    pass


class ValidationError(ProductboardError):
    """Validation error (400)."""

    pass


@dataclass
class PaginatedResponse:
    """Response with pagination support."""

    data: List[Dict[str, Any]]
    has_more: bool
    next_url: Optional[str]


class ProductboardClient:
    """
    Client for interacting with the Productboard API.

    Token is passed to each method call and never stored.
    """

    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        self.timeout = timeout
        self._session = requests.Session()

    def _get_headers(self, token: str) -> Dict[str, str]:
        """Get request headers with authorization."""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Version": "1",
        }

    def _calculate_backoff(self, attempt: int, retry_after: Optional[float] = None) -> float:
        """Calculate backoff time with exponential increase and jitter."""
        if retry_after:
            return retry_after

        backoff = min(INITIAL_BACKOFF * (2**attempt), MAX_BACKOFF)
        jitter = backoff * JITTER_FACTOR * random.random()
        return backoff + jitter

    def _make_request(
        self,
        method: str,
        url: str,
        token: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Make an HTTP request with retry logic.

        Retries on:
        - 429 (Rate Limited)
        - 5xx (Server Errors)
        - Connection errors
        """
        headers = self._get_headers(token)
        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_data,
                    params=params,
                    timeout=self.timeout,
                )

                # Handle rate limiting
                if response.status_code == 429:
                    if attempt < MAX_RETRIES - 1:
                        retry_after = response.headers.get("Retry-After")
                        wait_time = self._calculate_backoff(
                            attempt, float(retry_after) if retry_after else None
                        )
                        time.sleep(wait_time)
                        continue
                    raise RateLimitError(
                        "Rate limit exceeded after max retries",
                        retry_after=float(response.headers.get("Retry-After", 0)),
                    )

                # Handle server errors with retry
                if 500 <= response.status_code < 600:
                    if attempt < MAX_RETRIES - 1:
                        wait_time = self._calculate_backoff(attempt)
                        time.sleep(wait_time)
                        continue
                    raise ServerError(
                        f"Server error: {response.status_code}", response.status_code
                    )

                # Handle auth errors (no retry)
                if response.status_code == 401:
                    raise AuthError("Invalid API token", 401)

                if response.status_code == 403:
                    raise AuthError("Insufficient permissions", 403)

                # Handle not found
                if response.status_code == 404:
                    raise NotFoundError("Resource not found", 404)

                # Handle validation errors
                if response.status_code == 400:
                    error_detail = response.text[:200] if response.text else "Bad request"
                    raise ValidationError(f"Validation error: {error_detail}", 400)

                return response

            except requests.RequestException as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait_time = self._calculate_backoff(attempt)
                    time.sleep(wait_time)
                    continue
                raise ProductboardError(f"Request failed: {e}")

        # Should not reach here, but just in case
        if last_error:
            raise ProductboardError(f"Request failed after {MAX_RETRIES} attempts: {last_error}")
        raise ProductboardError(f"Request failed after {MAX_RETRIES} attempts")

    def _fetch_all_paginated(
        self,
        url: str,
        token: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all pages of a paginated endpoint."""
        all_data: List[Dict[str, Any]] = []
        current_url = url
        current_params = params

        while current_url:
            response = self._make_request("GET", current_url, token, params=current_params)
            data = response.json()

            all_data.extend(data.get("data", []))

            # Handle pagination
            links = data.get("links", {})
            current_url = links.get("next")
            current_params = None  # Next URL includes params

        return all_data

    # ==================== Product Hierarchy APIs ====================

    def fetch_products(self, token: str) -> List[Dict[str, Any]]:
        """Fetch all products."""
        return self._fetch_all_paginated(
            f"{API_BASE}/entities",
            token,
            params={"type[]": "product"},
        )

    def fetch_components(self, token: str) -> List[Dict[str, Any]]:
        """Fetch all components."""
        return self._fetch_all_paginated(
            f"{API_BASE}/entities",
            token,
            params={"type[]": "component"},
        )

    def fetch_features(self, token: str) -> List[Dict[str, Any]]:
        """Fetch all features."""
        return self._fetch_all_paginated(
            f"{API_BASE}/entities",
            token,
            params={"type[]": "feature"},
        )

    def update_entity(self, token: str, entity_id: str, new_name: str) -> bool:
        """Update an entity's name."""
        url = f"{API_BASE}/entities/{entity_id}"
        payload = {"data": {"fields": {"name": new_name}}}

        response = self._make_request("PATCH", url, token, json_data=payload)
        return response.status_code in (200, 204)

    # ==================== Strategy APIs ====================

    def fetch_objectives(self, token: str) -> List[Dict[str, Any]]:
        """Fetch all objectives."""
        return self._fetch_all_paginated(
            f"{API_BASE}/entities",
            token,
            params={"type[]": "objective"},
        )

    def fetch_key_results(self, token: str, objective_id: str) -> List[Dict[str, Any]]:
        """Fetch key results for a specific objective."""
        return self._fetch_all_paginated(
            f"{API_BASE}/entities",
            token,
            params={"type[]": "keyResult", "parent[id]": objective_id},
        )

    def fetch_initiatives(self, token: str) -> List[Dict[str, Any]]:
        """Fetch all initiatives."""
        return self._fetch_all_paginated(
            f"{API_BASE}/entities",
            token,
            params={"type[]": "initiative"},
        )

    def update_objective(self, token: str, objective_id: str, new_name: str) -> bool:
        """Update an objective's name."""
        url = f"{API_BASE}/entities/{objective_id}"
        payload = {"data": {"fields": {"name": new_name}}}

        response = self._make_request("PATCH", url, token, json_data=payload)
        return response.status_code in (200, 204)

    def update_key_result(self, token: str, kr_id: str, new_name: str) -> bool:
        """Update a key result's name."""
        url = f"{API_BASE}/entities/{kr_id}"
        payload = {"data": {"fields": {"name": new_name}}}

        response = self._make_request("PATCH", url, token, json_data=payload)
        return response.status_code in (200, 204)

    def update_initiative(self, token: str, initiative_id: str, new_name: str) -> bool:
        """Update an initiative's name."""
        url = f"{API_BASE}/entities/{initiative_id}"
        payload = {"data": {"fields": {"name": new_name}}}

        response = self._make_request("PATCH", url, token, json_data=payload)
        return response.status_code in (200, 204)

    # ==================== Company APIs (V2) ====================

    def get_or_create_company(
        self,
        token: str,
        company_name: str,
        domain: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get existing company by name or create a new one.

        Args:
            token: Productboard API token
            company_name: Company name to find or create
            domain: Optional domain for the company (e.g., "acme.com")

        Returns:
            Company ID if found/created, None otherwise.
        """
        # First, try to find existing company by name
        try:
            companies = self._fetch_all_paginated(
                f"{API_BASE}/entities",
                token,
                params={"type[]": "company"},
            )
            for company in companies:
                if company.get("fields", {}).get("name", "").lower() == company_name.lower():
                    return company.get("id")
        except ProductboardError:
            pass  # Continue to create

        # Company not found, create it
        url = f"{API_BASE}/entities"
        payload = {
            "data": {
                "type": "company",
                "fields": {
                    "name": company_name,
                }
            }
        }
        if domain:
            payload["data"]["fields"]["domain"] = domain

        response = self._make_request("POST", url, token, json_data=payload)

        if response.status_code in (200, 201):
            data = response.json()
            company_id = data.get("data", {}).get("id")
            # Brief delay for eventual consistency - newly created companies
            # aren't immediately available to the Notes API
            if company_id:
                time.sleep(1.5)
            return company_id
        return None

    # ==================== Notes APIs (V2) ====================
    #
    # V2 Notes API limitations and workarounds:
    # - Tags: V2 can't auto-create tags, so we append a searchable footer
    #   to the note content (e.g., "---\nDemo: CompanyName") for filtering
    # - Companies: We create the company first via /v2/entities, then link it
    #

    def create_note(
        self,
        token: str,
        title: str,
        content: str,
        customer_email: str,
        source_origin: str,
        source_record_id: str,
        company_name: str,
        demo_tag: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a note and return its ID (V2 API).

        Since V2 can't auto-create tags, we append a searchable footer to the
        note content for filtering purposes (e.g., "Demo: CompanyName").

        Args:
            token: Productboard API token
            title: Note title
            content: Note content
            customer_email: Customer's email address (used for user lookup)
            source_origin: Source system identifier
            source_record_id: Unique record ID from source system
            company_name: Company name (will be created if doesn't exist)
            demo_tag: Optional tag to append to content for filtering

        Returns:
            Note ID if created successfully, None otherwise.
        """
        # Step 1: Get or create the company
        company_id = self.get_or_create_company(token, company_name)

        # Step 2: Append searchable footer to content for filtering
        # This replaces tags since V2 can't auto-create them
        if demo_tag:
            content_with_footer = f"{content}\n\n---\nDemo: {demo_tag}"
        else:
            content_with_footer = content

        # Step 3: Build the V2 note payload
        url = f"{API_BASE}/notes"
        payload = {
            "data": {
                "type": "textNote",
                "fields": {
                    "name": title,
                    "content": content_with_footer,
                },
                "metadata": {
                    "system": source_origin,
                    "recordId": source_record_id,
                },
            }
        }

        # Step 4: Add company relationship if we have one
        if company_id:
            payload["data"]["relationships"] = [
                {
                    "type": "customer",
                    "target": {
                        "type": "company",
                        "id": company_id
                    }
                }
            ]

        response = self._make_request("POST", url, token, json_data=payload)

        if response.status_code in (200, 201):
            data = response.json()
            return data.get("data", {}).get("id")
        return None

    # ==================== Validation ====================

    def validate_token(self, token: str) -> bool:
        """
        Validate that the token is valid and has access to the space.

        Returns True if valid, raises AuthError if not.
        """
        try:
            # Try to fetch a minimal amount of data
            self._make_request(
                "GET",
                f"{API_BASE}/entities",
                token,
                params={"type[]": "product", "page[size]": 1},
            )
            return True
        except AuthError:
            raise
        except ProductboardError:
            return False


# Create a default client instance
default_client = ProductboardClient()
