"""Pages module for unified application."""

from . import (
    processor_page,
    failed_items_page,
    dashboard_receipts,
    dashboard_bank_transactions,
    dashboard_statistics,
    dashboard_export,
    rocskincare_workers,
    rocskincare_periods,
    rocskincare_image_upload,
    rocskincare_csv_upload,
    rocskincare_period_closure,
    rocskincare_visualization,
    admin_page,
    admin_test_receipt
)

__all__ = [
    'processor_page',
    'failed_items_page',
    'dashboard_receipts',
    'dashboard_bank_transactions',
    'dashboard_export',
    'rocskincare_workers',
    'rocskincare_periods',
    'rocskincare_image_upload',
    'rocskincare_csv_upload',
    'rocskincare_period_closure',
    'rocskincare_visualization',
    'admin_page',
    'admin_test_receipt'
]
