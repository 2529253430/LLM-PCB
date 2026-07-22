from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from ..models import (
    BuckDesignRequirements,
    ComponentCandidate,
    DistributorOffer,
    LifecycleStatus,
)
from ..provider import ComponentSearchProvider


JsonDict = Dict[str, Any]
Transport = Callable[
    [str, str, Mapping[str, str], Optional[bytes], float],
    Tuple[int, Mapping[str, str], bytes],
]


class DigiKeyError(Exception):
    """Base exception for DigiKey integration errors."""


class DigiKeyConfigurationError(DigiKeyError):
    """Raised when required DigiKey configuration is missing or invalid."""


class DigiKeyAuthenticationError(DigiKeyError):
    """Raised when OAuth authentication fails."""


class DigiKeyAPIError(DigiKeyError):
    """Raised when a DigiKey API request fails."""


@dataclass(frozen=True)
class DigiKeyConfiguration:
    """
    Configuration for DigiKey Product Information V4.

    Credentials should normally be supplied through environment variables:
    DIGIKEY_CLIENT_ID and DIGIKEY_CLIENT_SECRET.
    """

    client_id: str
    client_secret: str

    site: str = "US"
    language: str = "en"
    currency: str = "USD"
    ship_to_country: str = "US"

    api_base_url: str = "https://api.digikey.com"
    token_url: str = "https://api.digikey.com/v1/oauth2/token"

    timeout_seconds: float = 20.0
    cache_directory: Optional[Path] = None
    cache_ttl_seconds: int = 3600

    @classmethod
    def from_environment(
        cls,
        cache_directory: Optional[str | Path] = None,
    ) -> "DigiKeyConfiguration":
        client_id = os.getenv("DIGIKEY_CLIENT_ID", "").strip()
        client_secret = os.getenv("DIGIKEY_CLIENT_SECRET", "").strip()

        if not client_id or not client_secret:
            raise DigiKeyConfigurationError(
                "Missing DigiKey credentials. Set DIGIKEY_CLIENT_ID and "
                "DIGIKEY_CLIENT_SECRET environment variables."
            )

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            site=os.getenv("DIGIKEY_SITE", "US").strip() or "US",
            language=os.getenv("DIGIKEY_LANGUAGE", "en").strip() or "en",
            currency=os.getenv(
                "DIGIKEY_CURRENCY",
                "USD",
            ).strip() or "USD",
            ship_to_country=(
                os.getenv(
                    "DIGIKEY_SHIP_TO_COUNTRY",
                    "US",
                ).strip()
                or "US"
            ),
            cache_directory=(
                Path(cache_directory)
                if cache_directory is not None
                else None
            ),
        )

    def validate(self) -> None:
        if not self.client_id.strip():
            raise DigiKeyConfigurationError("client_id cannot be empty.")

        if not self.client_secret.strip():
            raise DigiKeyConfigurationError(
                "client_secret cannot be empty."
            )

        if self.timeout_seconds <= 0:
            raise DigiKeyConfigurationError(
                "timeout_seconds must be greater than zero."
            )

        if self.cache_ttl_seconds < 0:
            raise DigiKeyConfigurationError(
                "cache_ttl_seconds cannot be negative."
            )


@dataclass
class _AccessToken:
    value: str
    expires_at_epoch: float

    def is_valid(self, now_epoch: float) -> bool:
        return bool(self.value) and now_epoch < self.expires_at_epoch


class DigiKeyProvider(ComponentSearchProvider):
    """
    DigiKey Product Information V4 provider.

    The provider obtains OAuth credentials, performs product searches,
    normalizes DigiKey records, and returns ComponentCandidate objects.
    Engineering ranking remains the responsibility of the comparator.
    """

    SEARCH_PATH = "/products/v4/search/keyword"

    def __init__(
        self,
        configuration: DigiKeyConfiguration,
        transport: Optional[Transport] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        configuration.validate()

        self.configuration = configuration
        self._transport = transport or self._default_transport
        self._clock = clock
        self._access_token: Optional[_AccessToken] = None

        if self.configuration.cache_directory is not None:
            self.configuration.cache_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

    @property
    def provider_name(self) -> str:
        return "DigiKey"

    def search_buck_regulators(
        self,
        requirements: BuckDesignRequirements,
        limit: int = 50,
    ) -> List[ComponentCandidate]:
        requirements.validate()

        if limit <= 0:
            raise ValueError("limit must be greater than zero.")

        payload = self._build_keyword_search_payload(
            requirements,
            limit,
        )
        cache_key = self._build_cache_key(payload)

        cached = self._read_cache(cache_key)

        if cached is not None:
            response = cached
        else:
            response = self._request_json(
                method="POST",
                path=self.SEARCH_PATH,
                payload=payload,
            )
            self._write_cache(cache_key, response)

        products = self._extract_products(response)

        candidates: List[ComponentCandidate] = []

        for product in products:
            candidate = self._normalize_product(product)

            if candidate is not None:
                candidates.append(candidate)

        return candidates[:limit]

    def get_component(
        self,
        part_number: str,
        manufacturer: Optional[str] = None,
    ) -> Optional[ComponentCandidate]:
        cleaned = part_number.strip()

        if not cleaned:
            raise ValueError("part_number cannot be empty.")

        encoded = urllib.parse.quote(cleaned, safe="")

        response = self._request_json(
            method="GET",
            path=f"/products/v4/search/{encoded}/productdetails",
            payload=None,
        )

        product = (
            response.get("Product")
            or response.get("product")
            or response
        )

        if not isinstance(product, dict):
            return None

        candidate = self._normalize_product(product)

        if candidate is None:
            return None

        if (
            manufacturer is not None
            and candidate.manufacturer.strip().lower()
            != manufacturer.strip().lower()
        ):
            return None

        return candidate

    def _build_keyword_search_payload(
        self,
        requirements: BuckDesignRequirements,
        limit: int,
    ) -> JsonDict:
        keywords = (
            "buck switching regulator "
            f"{requirements.input_voltage_max_v:g}V "
            f"{requirements.output_current_a:g}A"
        )

        return {
            "Keywords": keywords,
            "RecordCount": min(limit, 50),
            "RecordStartPosition": 0,
            "ExcludeMarketPlaceProducts": True,
            "SearchOptions": (
                ["InStock"]
                if requirements.require_in_stock
                else []
            ),
            "Sort": {
                "SortOption": "SortByDigiKeyPartNumber",
                "Direction": "Ascending",
            },
        }

    def _request_json(
        self,
        method: str,
        path: str,
        payload: Optional[JsonDict],
    ) -> JsonDict:
        token = self._get_access_token()

        url = self.configuration.api_base_url.rstrip("/") + path

        body = (
            json.dumps(payload).encode("utf-8")
            if payload is not None
            else None
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "X-DIGIKEY-Client-Id": self.configuration.client_id,
            "X-DIGIKEY-Locale-Site": self.configuration.site,
            "X-DIGIKEY-Locale-Language": (
                self.configuration.language
            ),
            "X-DIGIKEY-Locale-Currency": (
                self.configuration.currency
            ),
            "X-DIGIKEY-Locale-ShipToCountry": (
                self.configuration.ship_to_country
            ),
            "Accept": "application/json",
        }

        if body is not None:
            headers["Content-Type"] = "application/json"

        status, _, response_body = self._transport(
            method,
            url,
            headers,
            body,
            self.configuration.timeout_seconds,
        )

        decoded = self._decode_json(response_body, url)

        if not 200 <= status < 300:
            message = self._extract_error_message(decoded)

            raise DigiKeyAPIError(
                f"DigiKey API returned HTTP {status}: {message}"
            )

        return decoded

    def _get_access_token(self) -> str:
        now = self._clock()

        if (
            self._access_token is not None
            and self._access_token.is_valid(now)
        ):
            return self._access_token.value

        form = urllib.parse.urlencode(
            {
                "client_id": self.configuration.client_id,
                "client_secret": self.configuration.client_secret,
                "grant_type": "client_credentials",
            }
        ).encode("utf-8")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        status, _, response_body = self._transport(
            "POST",
            self.configuration.token_url,
            headers,
            form,
            self.configuration.timeout_seconds,
        )

        decoded = self._decode_json(
            response_body,
            self.configuration.token_url,
        )

        if not 200 <= status < 300:
            message = self._extract_error_message(decoded)

            raise DigiKeyAuthenticationError(
                f"DigiKey OAuth returned HTTP {status}: {message}"
            )

        token = str(decoded.get("access_token", "")).strip()

        if not token:
            raise DigiKeyAuthenticationError(
                "DigiKey OAuth response did not contain access_token."
            )

        try:
            expires_in = float(decoded.get("expires_in", 600))
        except (TypeError, ValueError):
            expires_in = 600.0

        refresh_margin = min(
            60.0,
            max(5.0, expires_in * 0.10),
        )

        self._access_token = _AccessToken(
            value=token,
            expires_at_epoch=(
                now + max(1.0, expires_in - refresh_margin)
            ),
        )

        return token

    @staticmethod
    def _default_transport(
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[bytes],
        timeout_seconds: float,
    ) -> Tuple[int, Mapping[str, str], bytes]:
        request = urllib.request.Request(
            url=url,
            data=body,
            headers=dict(headers),
            method=method,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout_seconds,
            ) as response:
                return (
                    int(response.status),
                    dict(response.headers.items()),
                    response.read(),
                )

        except urllib.error.HTTPError as exc:
            return (
                int(exc.code),
                dict(exc.headers.items())
                if exc.headers
                else {},
                exc.read(),
            )

        except urllib.error.URLError as exc:
            raise DigiKeyAPIError(
                f"Unable to reach DigiKey API: {exc.reason}"
            ) from exc

        except TimeoutError as exc:
            raise DigiKeyAPIError(
                "DigiKey API request timed out."
            ) from exc

    @staticmethod
    def _decode_json(
        body: bytes,
        url: str,
    ) -> JsonDict:
        if not body:
            return {}

        try:
            decoded = json.loads(body.decode("utf-8"))
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise DigiKeyAPIError(
                f"Invalid JSON response from {url}."
            ) from exc

        if not isinstance(decoded, dict):
            raise DigiKeyAPIError(
                f"Expected a JSON object from {url}."
            )

        return decoded

    @staticmethod
    def _extract_error_message(
        response: Mapping[str, Any],
    ) -> str:
        for key in (
            "ErrorMessage",
            "error_description",
            "message",
            "Message",
            "error",
        ):
            value = response.get(key)

            if value:
                return str(value)

        return "Unknown DigiKey error"

    @staticmethod
    def _extract_products(
        response: Mapping[str, Any],
    ) -> List[JsonDict]:
        for key in (
            "Products",
            "products",
            "ProductSearchResults",
            "productSearchResults",
        ):
            value = response.get(key)

            if isinstance(value, list):
                return [
                    item
                    for item in value
                    if isinstance(item, dict)
                ]

        return []

    def _normalize_product(
        self,
        product: Mapping[str, Any],
    ) -> Optional[ComponentCandidate]:
        manufacturer = self._extract_name(
            product.get("Manufacturer")
            or product.get("manufacturer")
        )

        part_number = self._first_text(
            product,
            "ManufacturerProductNumber",
            "manufacturerProductNumber",
            "ManufacturerPartNumber",
            "manufacturerPartNumber",
        )

        if not manufacturer or not part_number:
            return None

        description = self._extract_description(product)
        parameters = self._parameter_map(product)

        topology_text = " ".join(
            [
                description,
                " ".join(parameters.values()),
            ]
        ).lower()

        if not any(
            keyword in topology_text
            for keyword in (
                "buck",
                "step-down",
                "step down",
            )
        ):
            return None

        offers = self._extract_offers(product)

        package_name = self._parameter_value(
            parameters,
            "Package / Case",
            "Package",
            "Supplier Device Package",
        )

        lifecycle = self._parse_lifecycle(
            self._first_text(
                product,
                "ProductStatus",
                "productStatus",
                "Status",
                "status",
            )
            or self._parameter_value(
                parameters,
                "Product Status",
            )
        )

        return ComponentCandidate(
            manufacturer=manufacturer,
            part_number=part_number,
            description=description,
            topology="buck",
            lifecycle_status=lifecycle,
            input_voltage_min_v=self._parse_number(
                self._parameter_value(
                    parameters,
                    "Voltage - Input (Min)",
                    "Voltage - Input",
                    "Input Voltage Min",
                )
            ),
            input_voltage_max_v=self._parse_max_number(
                self._parameter_value(
                    parameters,
                    "Voltage - Input (Max)",
                    "Voltage - Input",
                    "Input Voltage Max",
                )
            ),
            output_voltage_min_v=self._parse_number(
                self._parameter_value(
                    parameters,
                    "Voltage - Output (Min/Fixed)",
                    "Voltage - Output (Min)",
                )
            ),
            output_voltage_max_v=self._parse_max_number(
                self._parameter_value(
                    parameters,
                    "Voltage - Output (Max)",
                    "Voltage - Output",
                )
            ),
            output_current_max_a=self._parse_current_a(
                self._parameter_value(
                    parameters,
                    "Current - Output",
                    "Output Current",
                )
            ),
            switching_frequency_min_hz=(
                self._parse_frequency_hz(
                    self._parameter_value(
                        parameters,
                        "Frequency - Switching",
                        "Switching Frequency",
                    ),
                    choose_max=False,
                )
            ),
            switching_frequency_max_hz=(
                self._parse_frequency_hz(
                    self._parameter_value(
                        parameters,
                        "Frequency - Switching",
                        "Switching Frequency",
                    ),
                    choose_max=True,
                )
            ),
            synchronous_rectification=(
                self._parse_optional_bool(
                    self._parameter_value(
                        parameters,
                        "Synchronous Rectifier",
                        "Synchronous Rectification",
                    )
                )
            ),
            integrated_switches=self._infer_integrated_switches(
                description,
                parameters,
            ),
            package_name=package_name,
            operating_temperature_min_c=(
                self._parse_temperature(
                    self._parameter_value(
                        parameters,
                        "Operating Temperature",
                    ),
                    choose_max=False,
                )
            ),
            operating_temperature_max_c=(
                self._parse_temperature(
                    self._parameter_value(
                        parameters,
                        "Operating Temperature",
                    ),
                    choose_max=True,
                )
            ),
            datasheet_url=self._first_text(
                product,
                "DatasheetUrl",
                "datasheetUrl",
                "DatasheetURL",
            ),
            source_provider=self.provider_name,
            offers=offers,
            extra={
                "digikey_part_number": self._first_text(
                    product,
                    "DigiKeyPartNumber",
                    "digiKeyPartNumber",
                ),
                "parameters": parameters,
                "raw_category": self._extract_name(
                    product.get("Category")
                    or product.get("category")
                ),
            },
        )

    def _extract_offers(
        self,
        product: Mapping[str, Any],
    ) -> List[DistributorOffer]:
        product_variations = (
            product.get("ProductVariations")
            or product.get("productVariations")
            or []
        )

        offers: List[DistributorOffer] = []

        if isinstance(product_variations, list):
            for variation in product_variations:
                if not isinstance(variation, dict):
                    continue

                sku = self._first_text(
                    variation,
                    "DigiKeyProductNumber",
                    "digiKeyProductNumber",
                )

                stock = self._first_int(
                    variation,
                    "QuantityAvailableforPackageType",
                    "quantityAvailableforPackageType",
                    "QuantityAvailable",
                    "quantityAvailable",
                )

                unit_price, currency = (
                    self._extract_lowest_price(variation)
                )

                offers.append(
                    DistributorOffer(
                        distributor="DigiKey",
                        sku=sku,
                        unit_price=unit_price,
                        currency=(
                            currency
                            or self.configuration.currency
                        ),
                        stock_quantity=stock,
                        minimum_order_quantity=(
                            self._first_int(
                                variation,
                                "MinimumOrderQuantity",
                                "minimumOrderQuantity",
                            )
                            or 1
                        ),
                        lead_time_days=self._first_int(
                            variation,
                            "ManufacturerLeadWeeks",
                            "manufacturerLeadWeeks",
                        ),
                        product_url=self._first_text(
                            variation,
                            "ProductUrl",
                            "productUrl",
                        ),
                        last_updated_iso=datetime.now(
                            timezone.utc
                        ).isoformat(),
                    )
                )

        if not offers:
            unit_price, currency = (
                self._extract_lowest_price(product)
            )

            offers.append(
                DistributorOffer(
                    distributor="DigiKey",
                    sku=self._first_text(
                        product,
                        "DigiKeyPartNumber",
                        "digiKeyPartNumber",
                    ),
                    unit_price=unit_price,
                    currency=(
                        currency
                        or self.configuration.currency
                    ),
                    stock_quantity=self._first_int(
                        product,
                        "QuantityAvailable",
                        "quantityAvailable",
                    ),
                    minimum_order_quantity=1,
                    product_url=self._first_text(
                        product,
                        "ProductUrl",
                        "productUrl",
                    ),
                    last_updated_iso=datetime.now(
                        timezone.utc
                    ).isoformat(),
                )
            )

        return offers

    def _extract_lowest_price(
        self,
        source: Mapping[str, Any],
    ) -> Tuple[Optional[float], Optional[str]]:
        pricing = (
            source.get("StandardPricing")
            or source.get("standardPricing")
            or source.get("Pricing")
            or source.get("pricing")
            or []
        )

        prices: List[Tuple[float, Optional[str]]] = []

        if isinstance(pricing, list):
            for entry in pricing:
                if not isinstance(entry, dict):
                    continue

                value = self._first_number(
                    entry,
                    "UnitPrice",
                    "unitPrice",
                    "Price",
                    "price",
                )

                currency = self._first_text(
                    entry,
                    "Currency",
                    "currency",
                )

                if value is not None:
                    prices.append((value, currency))

        if not prices:
            direct = self._first_number(
                source,
                "UnitPrice",
                "unitPrice",
            )

            currency = self._first_text(
                source,
                "Currency",
                "currency",
            )

            return direct, currency

        return min(prices, key=lambda item: item[0])

    @staticmethod
    def _extract_name(value: Any) -> Optional[str]:
        if isinstance(value, str):
            return value.strip() or None

        if isinstance(value, dict):
            for key in (
                "Name",
                "name",
                "Text",
                "text",
                "Value",
                "value",
            ):
                item = value.get(key)

                if isinstance(item, str) and item.strip():
                    return item.strip()

        return None

    @staticmethod
    def _extract_description(
        product: Mapping[str, Any],
    ) -> str:
        description = (
            product.get("Description")
            or product.get("description")
            or {}
        )

        if isinstance(description, str):
            return description.strip()

        if isinstance(description, dict):
            for key in (
                "ProductDescription",
                "productDescription",
                "DetailedDescription",
                "detailedDescription",
                "Text",
                "text",
            ):
                value = description.get(key)

                if isinstance(value, str) and value.strip():
                    return value.strip()

        return ""

    def _parameter_map(
        self,
        product: Mapping[str, Any],
    ) -> Dict[str, str]:
        raw_parameters = (
            product.get("Parameters")
            or product.get("parameters")
            or []
        )

        result: Dict[str, str] = {}

        if not isinstance(raw_parameters, list):
            return result

        for entry in raw_parameters:
            if not isinstance(entry, dict):
                continue

            name = self._first_text(
                entry,
                "ParameterText",
                "parameterText",
                "Name",
                "name",
            )

            value = self._first_text(
                entry,
                "ValueText",
                "valueText",
                "Value",
                "value",
            )

            if name and value:
                result[name] = value

        return result

    @staticmethod
    def _parameter_value(
        parameters: Mapping[str, str],
        *names: str,
    ) -> Optional[str]:
        normalized = {
            key.strip().lower(): value
            for key, value in parameters.items()
        }

        for name in names:
            value = normalized.get(name.strip().lower())

            if value is not None:
                return value

        return None

    @staticmethod
    def _parse_lifecycle(
        value: Optional[str],
    ) -> LifecycleStatus:
        if not value:
            return LifecycleStatus.UNKNOWN

        normalized = value.strip().lower()

        if (
            "obsolete" in normalized
            or "discontinued" in normalized
        ):
            return LifecycleStatus.OBSOLETE

        if (
            "not recommended" in normalized
            or "nrnd" in normalized
        ):
            return (
                LifecycleStatus
                .NOT_RECOMMENDED_FOR_NEW_DESIGNS
            )

        if "active" in normalized:
            return LifecycleStatus.ACTIVE

        return LifecycleStatus.UNKNOWN

    @staticmethod
    def _parse_optional_bool(
        value: Optional[str],
    ) -> Optional[bool]:
        if value is None:
            return None

        normalized = value.strip().lower()

        if normalized in {"yes", "true", "1"}:
            return True

        if normalized in {"no", "false", "0"}:
            return False

        return None

    @staticmethod
    def _infer_integrated_switches(
        description: str,
        parameters: Mapping[str, str],
    ) -> Optional[bool]:
        text = (
            description
            + " "
            + " ".join(parameters.values())
        ).lower()

        if "controller" in text and "regulator" not in text:
            return False

        if (
            "switching regulator" in text
            or "dc dc converter" in text
        ):
            return True

        return None

    @classmethod
    def _parse_number(
        cls,
        value: Optional[str],
    ) -> Optional[float]:
        values = cls._extract_numeric_values(value)
        return values[0] if values else None

    @classmethod
    def _parse_max_number(
        cls,
        value: Optional[str],
    ) -> Optional[float]:
        values = cls._extract_numeric_values(value)
        return max(values) if values else None

    @classmethod
    def _parse_current_a(
        cls,
        value: Optional[str],
    ) -> Optional[float]:
        if value is None:
            return None

        matches = re.findall(
            r"([-+]?\d+(?:\.\d+)?)\s*(µA|uA|mA|A)\b",
            value,
            flags=re.IGNORECASE,
        )

        converted: List[float] = []

        for number_text, unit_text in matches:
            number = float(number_text)
            unit = unit_text.lower()

            if unit in {"µa", "ua"}:
                number /= 1_000_000.0
            elif unit == "ma":
                number /= 1_000.0

            converted.append(number)

        if converted:
            return max(converted)

        values = cls._extract_numeric_values(value)
        return max(values) if values else None

    @classmethod
    def _parse_frequency_hz(
        cls,
        value: Optional[str],
        choose_max: bool,
    ) -> Optional[float]:
        """
        Parse frequency ranges while preserving each number's own unit.

        Example:
            "200kHz ~ 1.2MHz"
            -> [200_000, 1_200_000]

        The previous implementation detected "MHz" anywhere in the complete
        string and incorrectly multiplied both numbers by 1e6.
        """
        if value is None:
            return None

        matches = re.findall(
            r"([-+]?\d+(?:\.\d+)?)\s*(GHz|MHz|kHz|Hz)\b",
            value,
            flags=re.IGNORECASE,
        )

        frequencies: List[float] = []

        unit_factors = {
            "hz": 1.0,
            "khz": 1_000.0,
            "mhz": 1_000_000.0,
            "ghz": 1_000_000_000.0,
        }

        for number_text, unit_text in matches:
            number = float(number_text)
            factor = unit_factors[unit_text.lower()]
            frequencies.append(number * factor)

        if not frequencies:
            values = cls._extract_numeric_values(value)

            if not values:
                return None

            frequencies = values

        if choose_max:
            return max(frequencies)

        return min(frequencies)

    @classmethod
    def _parse_temperature(
        cls,
        value: Optional[str],
        choose_max: bool,
    ) -> Optional[float]:
        values = cls._extract_numeric_values(value)

        if not values:
            return None

        return max(values) if choose_max else min(values)

    @staticmethod
    def _extract_numeric_values(
        value: Optional[str],
    ) -> List[float]:
        if value is None:
            return []

        cleaned = (
            value.replace(",", "")
            .replace("−", "-")
            .replace("–", "-")
        )

        pattern = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"

        result: List[float] = []

        for token in re.findall(pattern, cleaned):
            try:
                result.append(float(token))
            except ValueError:
                continue

        return result

    @staticmethod
    def _first_text(
        source: Mapping[str, Any],
        *keys: str,
    ) -> Optional[str]:
        for key in keys:
            value = source.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

    @staticmethod
    def _first_number(
        source: Mapping[str, Any],
        *keys: str,
    ) -> Optional[float]:
        for key in keys:
            value = source.get(key)

            if isinstance(value, bool):
                continue

            if isinstance(value, (int, float)):
                return float(value)

            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    continue

        return None

    @staticmethod
    def _first_int(
        source: Mapping[str, Any],
        *keys: str,
    ) -> Optional[int]:
        number = DigiKeyProvider._first_number(
            source,
            *keys,
        )

        return int(number) if number is not None else None

    @staticmethod
    def _build_cache_key(
        payload: Mapping[str, Any],
    ) -> str:
        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    def _cache_path(
        self,
        cache_key: str,
    ) -> Optional[Path]:
        directory = self.configuration.cache_directory

        if directory is None:
            return None

        return directory / f"digikey_{cache_key}.json"

    def _read_cache(
        self,
        cache_key: str,
    ) -> Optional[JsonDict]:
        path = self._cache_path(cache_key)

        if path is None or not path.exists():
            return None

        age = self._clock() - path.stat().st_mtime

        if age > self.configuration.cache_ttl_seconds:
            return None

        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return None

        return data if isinstance(data, dict) else None

    def _write_cache(
        self,
        cache_key: str,
        response: JsonDict,
    ) -> None:
        path = self._cache_path(cache_key)

        if path is None:
            return

        temporary = path.with_suffix(".tmp")

        temporary.write_text(
            json.dumps(
                response,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        temporary.replace(path)