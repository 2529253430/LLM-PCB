from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Tuple

import pytest

from src.sourcing.models import BuckDesignRequirements, LifecycleStatus
from src.sourcing.providers.digikey_provider import (
    DigiKeyAPIError,
    DigiKeyAuthenticationError,
    DigiKeyConfiguration,
    DigiKeyProvider,
)


class FakeTransport:
    def __init__(self) -> None:
        self.calls = []

    def __call__(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[bytes],
        timeout: float,
    ) -> Tuple[int, Mapping[str, str], bytes]:
        self.calls.append((method, url, dict(headers), body, timeout))

        if url.endswith("/v1/oauth2/token"):
            return (
                200,
                {},
                json.dumps(
                    {
                        "access_token": "test-token",
                        "expires_in": 600,
                    }
                ).encode("utf-8"),
            )

        if url.endswith("/products/v4/search/keyword"):
            return (
                200,
                {},
                json.dumps(_search_response()).encode("utf-8"),
            )

        raise AssertionError(f"Unexpected URL: {url}")


def _configuration(
    cache_directory: Optional[Path] = None,
) -> DigiKeyConfiguration:
    return DigiKeyConfiguration(
        client_id="client-id",
        client_secret="client-secret",
        site="SG",
        language="en",
        currency="SGD",
        ship_to_country="SG",
        cache_directory=cache_directory,
    )


def _requirements() -> BuckDesignRequirements:
    return BuckDesignRequirements(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
        quantity=5,
        currency="SGD",
    )


def _search_response():
    return {
        "Products": [
            {
                "Manufacturer": {"Name": "Example Semiconductor"},
                "ManufacturerProductNumber": "EX36S4",
                "DigiKeyPartNumber": "EX36S4-DK",
                "Description": {
                    "ProductDescription": (
                        "36V 4A synchronous buck switching regulator"
                    )
                },
                "ProductStatus": "Active",
                "DatasheetUrl": "https://example.invalid/ex36s4.pdf",
                "Parameters": [
                    {
                        "ParameterText": "Voltage - Input (Min)",
                        "ValueText": "4.5V",
                    },
                    {
                        "ParameterText": "Voltage - Input (Max)",
                        "ValueText": "36V",
                    },
                    {
                        "ParameterText": "Voltage - Output (Min/Fixed)",
                        "ValueText": "0.8V",
                    },
                    {
                        "ParameterText": "Voltage - Output (Max)",
                        "ValueText": "30V",
                    },
                    {
                        "ParameterText": "Current - Output",
                        "ValueText": "4A",
                    },
                    {
                        "ParameterText": "Frequency - Switching",
                        "ValueText": "200kHz ~ 1.2MHz",
                    },
                    {
                        "ParameterText": "Synchronous Rectifier",
                        "ValueText": "Yes",
                    },
                    {
                        "ParameterText": "Package / Case",
                        "ValueText": "16-VFQFN",
                    },
                    {
                        "ParameterText": "Operating Temperature",
                        "ValueText": "-40°C ~ 125°C",
                    },
                ],
                "ProductVariations": [
                    {
                        "DigiKeyProductNumber": "EX36S4TR-DK",
                        "QuantityAvailableforPackageType": 1250,
                        "MinimumOrderQuantity": 1,
                        "ProductUrl": (
                            "https://example.invalid/product/ex36s4"
                        ),
                        "StandardPricing": [
                            {
                                "BreakQuantity": 1,
                                "UnitPrice": 4.20,
                                "Currency": "SGD",
                            },
                            {
                                "BreakQuantity": 10,
                                "UnitPrice": 3.70,
                                "Currency": "SGD",
                            },
                        ],
                    }
                ],
            },
            {
                "Manufacturer": {"Name": "Not A Buck Company"},
                "ManufacturerProductNumber": "LINEAR1",
                "Description": {
                    "ProductDescription": "Linear voltage regulator"
                },
                "Parameters": [],
            },
        ]
    }


def test_search_normalizes_digikey_product() -> None:
    transport = FakeTransport()
    provider = DigiKeyProvider(
        _configuration(),
        transport=transport,
        clock=lambda: 1000.0,
    )

    candidates = provider.search_buck_regulators(_requirements())

    assert len(candidates) == 1

    candidate = candidates[0]
    assert candidate.manufacturer == "Example Semiconductor"
    assert candidate.part_number == "EX36S4"
    assert candidate.lifecycle_status == LifecycleStatus.ACTIVE
    assert candidate.input_voltage_min_v == 4.5
    assert candidate.input_voltage_max_v == 36.0
    assert candidate.output_current_max_a == 4.0
    assert candidate.switching_frequency_min_hz == 200_000
    assert candidate.switching_frequency_max_hz == 1_200_000
    assert candidate.synchronous_rectification is True
    assert candidate.operating_temperature_min_c == -40.0
    assert candidate.operating_temperature_max_c == 125.0
    assert candidate.source_provider == "DigiKey"

    offer = candidate.best_offer(5, "SGD")
    assert offer is not None
    assert offer.stock_quantity == 1250
    assert offer.unit_price == 3.70


def test_provider_uses_locale_headers() -> None:
    transport = FakeTransport()
    provider = DigiKeyProvider(
        _configuration(),
        transport=transport,
    )

    provider.search_buck_regulators(_requirements())

    search_call = transport.calls[1]
    headers = search_call[2]

    assert headers["X-DIGIKEY-Locale-Site"] == "SG"
    assert headers["X-DIGIKEY-Locale-Currency"] == "SGD"
    assert headers["X-DIGIKEY-Locale-ShipToCountry"] == "SG"
    assert headers["Authorization"] == "Bearer test-token"


def test_access_token_is_reused() -> None:
    transport = FakeTransport()
    provider = DigiKeyProvider(
        _configuration(),
        transport=transport,
        clock=lambda: 1000.0,
    )

    provider.search_buck_regulators(_requirements())
    provider.search_buck_regulators(_requirements())

    token_calls = [
        call
        for call in transport.calls
        if call[1].endswith("/v1/oauth2/token")
    ]

    assert len(token_calls) == 1


def test_cache_prevents_second_search_request(
    tmp_path: Path,
) -> None:
    transport = FakeTransport()
    provider = DigiKeyProvider(
        _configuration(tmp_path),
        transport=transport,
        clock=lambda: 1000.0,
    )

    provider.search_buck_regulators(_requirements())
    provider.search_buck_regulators(_requirements())

    search_calls = [
        call
        for call in transport.calls
        if call[1].endswith("/products/v4/search/keyword")
    ]

    assert len(search_calls) == 1


def test_authentication_error_is_clear() -> None:
    def transport(method, url, headers, body, timeout):
        return (
            401,
            {},
            json.dumps(
                {"error_description": "invalid client"}
            ).encode("utf-8"),
        )

    provider = DigiKeyProvider(
        _configuration(),
        transport=transport,
    )

    with pytest.raises(
        DigiKeyAuthenticationError,
        match="invalid client",
    ):
        provider.search_buck_regulators(_requirements())


def test_api_error_is_clear() -> None:
    call_count = 0

    def transport(method, url, headers, body, timeout):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            return (
                200,
                {},
                json.dumps(
                    {
                        "access_token": "token",
                        "expires_in": 600,
                    }
                ).encode("utf-8"),
            )

        return (
            429,
            {},
            json.dumps(
                {"message": "rate limit exceeded"}
            ).encode("utf-8"),
        )

    provider = DigiKeyProvider(
        _configuration(),
        transport=transport,
    )

    with pytest.raises(
        DigiKeyAPIError,
        match="rate limit exceeded",
    ):
        provider.search_buck_regulators(_requirements())
