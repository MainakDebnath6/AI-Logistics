"""Horizon-gated forecast-to-capacity advisory calculations."""

from app.schemas.hgfc import HGFCRequest, HGFCResponse, HGFCStatus


class HGFCService:
    """Compute advisory capacity risk without changing operational demand."""

    def __init__(self, advisory_horizon_days: int = 14) -> None:
        if advisory_horizon_days < 1:
            raise ValueError("Advisory horizon must be at least one day.")
        self._advisory_horizon_days = advisory_horizon_days

    def assess(self, request: HGFCRequest) -> HGFCResponse:
        """Return a risk signal only when the forecast is inside the gate."""
        gate_open = request.horizon_days <= self._advisory_horizon_days
        if not gate_open:
            return HGFCResponse(
                forecast_demand=request.forecast_demand,
                available_capacity=request.available_capacity,
                horizon_days=request.horizon_days,
                advisory_horizon_days=self._advisory_horizon_days,
                gate_open=False,
                status=HGFCStatus.OUTSIDE_HORIZON,
                capacity_delta=None,
                rho=None,
                capacity_risk=None,
                recommended_additional_capacity=0.0,
                preparation_recommended=False,
            )

        capacity_delta = request.forecast_demand - request.available_capacity
        capacity_risk = max(0.0, capacity_delta)
        rho = (
            request.forecast_demand / request.available_capacity
            if request.available_capacity > 0
            else None
        )
        shortfall = capacity_risk > 0

        return HGFCResponse(
            forecast_demand=request.forecast_demand,
            available_capacity=request.available_capacity,
            horizon_days=request.horizon_days,
            advisory_horizon_days=self._advisory_horizon_days,
            gate_open=True,
            status=(
                HGFCStatus.CAPACITY_SHORTFALL
                if shortfall
                else HGFCStatus.WITHIN_CAPACITY
            ),
            capacity_delta=capacity_delta,
            rho=rho,
            capacity_risk=capacity_risk,
            recommended_additional_capacity=capacity_risk,
            preparation_recommended=shortfall,
        )