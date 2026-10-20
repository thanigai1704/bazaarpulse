"""REST endpoint for the statistical analysis layer."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.analysis import compute_market_analysis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("")
def market_analysis(db: Session = Depends(get_db)):
    """Full descriptive-statistics report over the real catalogue.

    Returns price dispersion, discount depth, brand concentration (HHI),
    correlations, outlier flags and data-quality diagnostics. Computed
    on-demand from the products table (no cached copy — the dataset is
    static, so a request costs ~100ms).
    """
    return compute_market_analysis(db)
