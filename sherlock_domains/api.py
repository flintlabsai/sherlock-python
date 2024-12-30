"""Low level functions for interacting with Sherlock's API."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_api.ipynb.

# %% auto 0
__all__ = ['API_URL', 'PaymentMethodType', 'NewChallengeRequest', 'NewChallengeResponse', 'get_new_challenge',
           'AgentLoginRequest', 'AgentLoginResponse', 'agent_login', 'DomainResult', 'DomainSearchResponse', 'search',
           'ContactInformation', 'DomainPurchaseRequest', 'L402Offer', 'L402Response', 'request_offer',
           'PaymentRequest', 'PaymentMethod', 'PaymentRequestResponse', 'get_payment_request', 'DomainInfo',
           'get_domains', 'DNSRecord', 'get_dns_records', 'CreateDNSRecord', 'CreateDNSRecordRequest',
           'create_dns_record', 'UpdateDNSRecord', 'UpdateDNSRecordRequest', 'update_dns_records',
           'DeleteDNSRecordResponse', 'delete_dns_records']

# %% ../nbs/01_api.ipynb 3
import httpx
from datetime import datetime
from typing import Literal, List, Optional, TypedDict

from fastcore.test import *
from .keys import load_key

# %% ../nbs/01_api.ipynb 4
API_URL = "https://api.sherlockdomains.com"

# %% ../nbs/01_api.ipynb 6
class NewChallengeRequest(TypedDict):
    public_key: str

class NewChallengeResponse(TypedDict):
    challenge: str
    expires_at: datetime

def get_new_challenge(public_key_hex: str) -> str:
    """Get a new challenge for a given public key."""
    response = httpx.post(
        f"{API_URL}/api/v0/auth/challenge",
        json={"public_key": public_key_hex},
        headers={"Content-Type": "application/json"},
    )
    
    response.raise_for_status()
    response_data = NewChallengeResponse(**response.json())
    return response_data["challenge"]


# %% ../nbs/01_api.ipynb 8
class AgentLoginRequest(TypedDict):
    public_key: str
    challenge: str
    signature: str

class AgentLoginResponse(TypedDict):
    access: str
    refresh: str

def agent_login(public_key_hex: str, challenge: str, signature: str) -> tuple[str, str]:
    """Submit login request with signed challenge to get access and refresh tokens."""
    response = httpx.post(
        f"{API_URL}/api/v0/auth/login",
        json={"public_key": public_key_hex, "challenge": challenge, "signature": signature},
        headers={"Content-Type": "application/json"},
    )
    
    response.raise_for_status()
    response_data = AgentLoginResponse(**response.json())
    return response_data["access"], response_data["refresh"]

# %% ../nbs/01_api.ipynb 13
class DomainResult(TypedDict):
    name: str
    tld: str
    tags: Optional[List[str]]
    price: float
    currency: str
    available: bool

class DomainSearchResponse(TypedDict):
    id: str
    created_at: datetime
    available: List[DomainResult]
    unavailable: List[DomainResult]


def search(query: str, access_token: Optional[str] = None) -> DomainSearchResponse:
    """Perform a domain search with optional authentication."""
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")
    
    # Remove leading/trailing spaces and ensure no spaces in middle
    parts = query.strip().split()
    if len(parts) > 1:
        raise ValueError(f"Search query cannot contain spaces: {query}")
    
    query = parts[0]
    
    # If we have an access token send it in the headers
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    response = httpx.get(
        f"{API_URL}/api/v0/domains/search",
        params={"query": query},
        headers=headers
    )
    
    if response.status_code == 400:
        raise ValueError(response.json().get("detail", "Invalid search query"))
    
    response.raise_for_status()
    return DomainSearchResponse(**response.json())

# %% ../nbs/01_api.ipynb 17
class ContactInformation(TypedDict):
    first_name: str
    last_name: str
    email: str
    address: str
    city: str
    state: str
    country: str
    postal_code: str

class DomainPurchaseRequest(TypedDict):
    domain: str
    search_id: str
    contact_information: ContactInformation


# TODO: use the L402 client library when we have it


class L402Offer(TypedDict):
    id: str
    title: str
    description: str
    type: str
    amount: int
    currency: str
    payment_methods: List[str]

class L402Response(TypedDict):
    version: str
    payment_request_url: str
    payment_context_token: str
    offers: List[L402Offer]

def request_offer(search_id: str, domain: str, contact_information: ContactInformation, access_token: str) -> L402Response:
    """Request a purchase offer for a domain."""
    # TODO: validate contact information

    headers = {"Authorization": f"Bearer {access_token}"}

    data: DomainPurchaseRequest = {
        "domain": domain,
        "search_id": search_id,
        "contact_information": contact_information,
    }

    response = httpx.post(
        f"{API_URL}/api/v0/domains/purchase",
        json=data,
        headers=headers
    )

    if response.status_code != 402:
        response.raise_for_status()
        # If raise for status is not an error it means we got a 200s but that is not 
        # expected here.
        raise ValueError(f"Unexpected status code: {response.status_code}: {response.text}")

    return L402Response(**response.json())


# %% ../nbs/01_api.ipynb 21
PaymentMethodType = Literal["credit_card", "lightning"]

class PaymentRequest(TypedDict):
    offer_id: str
    payment_method: PaymentMethodType
    payment_context_token: str

class PaymentMethod(TypedDict, total=False):
    checkout_url: str
    lightning_invoice: str

class PaymentRequestResponse(TypedDict):
    payment_method: PaymentMethod
    expires_at: datetime

def get_payment_request(
    request_url: str,
    context_token: str,
    offer_id: str,
    payment_method: PaymentMethodType
) -> PaymentRequestResponse:
    headers = {
        "Authorization": f"L402 {context_token}"
    }
    
    data: PaymentRequest = {
        "offer_id": offer_id,
        "payment_method": payment_method,
        "payment_context_token": context_token
    }
    
    response = httpx.post(
        request_url,
        json=data, 
        headers=headers,
    )
    response.raise_for_status()
    
    return response.json()

# %% ../nbs/01_api.ipynb 25
class DomainInfo(TypedDict):
    id: str
    domain_name: str
    created_at: datetime
    expires_at: datetime
    auto_renew: bool
    locked: bool
    private: bool
    nameservers: List[str]
    status: str

def get_domains(access_token: str) -> List[DomainInfo]:    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = httpx.get(
        f"{API_URL}/api/v0/domains/domains",
        headers=headers
    )
    response.raise_for_status()
    
    return response.json()

# %% ../nbs/01_api.ipynb 31
class DNSRecord(TypedDict):
    id: str
    type: str
    name: str
    value: str
    ttl: int

def get_dns_records(domain_id: str, access_token: str) -> List[DNSRecord]:
    """Get DNS records for a domain."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = httpx.get(
        f"{API_URL}/api/v0/domains/{domain_id}/dns/records",
        headers=headers
    )
    response.raise_for_status()
    
    return response.json()["records"]


# %% ../nbs/01_api.ipynb 34
class CreateDNSRecord(TypedDict):
    type: str
    name: str
    value: str
    ttl: int

class CreateDNSRecordRequest(TypedDict):
    records: List[CreateDNSRecord]

def create_dns_record(
    domain_id: str, 
    record_type: str,
    name: str,
    value: str,
    ttl: int,
    access_token: str
) -> List[DNSRecord]:
    """Create a new DNS record for a domain."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    data: CreateDNSRecordRequest = {
        "records": [{
            "type": record_type,
            "name": name,
            "value": value,
            "ttl": ttl
        }]
    }
    
    response = httpx.post(
        f"{API_URL}/api/v0/domains/{domain_id}/dns/records",
        json=data,
        headers=headers
    )
    response.raise_for_status()
    
    return response.json()["records"]

# %% ../nbs/01_api.ipynb 37
class UpdateDNSRecord(TypedDict):
    id: str
    type: str
    name: str
    value: str
    ttl: int

class UpdateDNSRecordRequest(TypedDict):
    records: List[UpdateDNSRecord]

def update_dns_records(
    domain_id: str,
    records: List[UpdateDNSRecord],
    access_token: str
) -> List[DNSRecord]:
    """Update DNS records for a domain."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    data: UpdateDNSRecordRequest = {
        "records": records
    }
    
    response = httpx.patch(
        f"{API_URL}/api/v0/domains/{domain_id}/dns/records",
        json=data,
        headers=headers
    )
    response.raise_for_status()
    
    return response.json()["records"]

# %% ../nbs/01_api.ipynb 40
class DeleteDNSRecordResponse(TypedDict):
    domain: str
    deleted_records: List[str]

def delete_dns_records(
    domain_id: str,
    record_ids: List[str],
    access_token: str
) -> DeleteDNSRecordResponse:
    """Delete DNS records for a domain."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    data = {
        "record_ids": record_ids
    }
    
    response = httpx.Client().request(
        "DELETE",
        f"{API_URL}/api/v0/domains/{domain_id}/dns/records",
        json=data,
        headers=headers
    )
    response.raise_for_status()
    
    return response.json()