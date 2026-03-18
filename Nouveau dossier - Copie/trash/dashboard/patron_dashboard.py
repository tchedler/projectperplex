"""Legacy package for backwards compatibility.

This module exists to preserve older import paths such as:

    from dashboard.patron_dashboard import PatronDashboard

It simply proxies to the current implementation under interface/patron_dashboard.py.
"""

from interface.patron_dashboard import PatronDashboard

__all__ = ["PatronDashboard"]
