"""
Analytics and Dashboard endpoints for CLM API.
Provides comprehensive metrics and statistics for
contracts, measurements, and payments.
"""

from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Count, Sum, Q
from django.db.models.functions import Coalesce, TruncMonth, TruncDay
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Contract, Measurement, Payment, AuditLog


def error_response(detail, status_code):
    return Response(
        {"error": {"detail": detail}},
        status=status_code,
    )

# ========== Serializers ==========


class ContractMetricsSerializer(serializers.Serializer):
    """Metrics for contracts"""

    total_contracts = serializers.IntegerField()
    active_contracts = serializers.IntegerField()
    closed_contracts = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_remaining = serializers.DecimalField(max_digits=15, decimal_places=2)
    avg_contract_value = serializers.DecimalField(
        max_digits=15, decimal_places=2
    )
    percentage_completed = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )


class MeasurementMetricsSerializer(serializers.Serializer):
    """Metrics for measurements"""

    total_measurements = serializers.IntegerField()
    pending_measurements = serializers.IntegerField()
    approved_measurements = serializers.IntegerField()
    rejected_measurements = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    approved_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    avg_measurement_value = serializers.DecimalField(
        max_digits=15, decimal_places=2
    )


class PaymentMetricsSerializer(serializers.Serializer):
    """Metrics for payments"""

    total_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    paid_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    avg_payment_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2
    )


class ManagerPerformanceSerializer(serializers.Serializer):
    """Performance metrics by manager"""

    manager_id = serializers.IntegerField()
    manager_name = serializers.CharField()
    total_contracts = serializers.IntegerField()
    active_contracts = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    completed_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )


class TimelineDataSerializer(serializers.Serializer):
    """Timeline data for trends"""

    period = serializers.DateField()
    contracts_created = serializers.IntegerField()
    measurements_created = serializers.IntegerField()
    payments_made = serializers.IntegerField()
    total_paid = serializers.DecimalField(max_digits=15, decimal_places=2)


class OverviewSerializer(serializers.Serializer):
    """Complete system overview"""

    contracts = ContractMetricsSerializer()
    measurements = MeasurementMetricsSerializer()
    payments = PaymentMetricsSerializer()
    recent_activities = serializers.ListField(child=serializers.DictField())


class FinancialSummarySerializer(serializers.Serializer):
    """Detailed financial summary"""

    total_contracted = serializers.DecimalField(
        max_digits=15, decimal_places=2
    )
    total_measured = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_pending_payments = serializers.DecimalField(
        max_digits=15, decimal_places=2
    )
    total_remaining_balance = serializers.DecimalField(
        max_digits=15, decimal_places=2
    )
    measurement_to_contract_ratio = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )
    payment_to_measurement_ratio = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )
    overall_completion_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )


class StatusDistributionSerializer(serializers.Serializer):
    """Status distribution"""

    status = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


# ========== ViewSet ==========


class AnalyticsViewSet(viewsets.ViewSet):
    """
    Analytics and Dashboard endpoints.
    Provides comprehensive metrics and statistics.

    Endpoints:
    - GET /analytics/overview/ - Complete system overview
    - GET /analytics/contracts/ - Contract-specific metrics
    - GET /analytics/measurements/ - Measurement metrics
    - GET /analytics/payments/ - Payment metrics
    - GET /analytics/by_manager/ - Performance by manager
    - GET /analytics/financial/ - Detailed financial analysis
    - GET /analytics/timeline/ - Time-series data for trends
    - GET /analytics/status_distribution/ - Status breakdowns
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_base_queryset(self, user):
        """
        Get base queryset filtered by user permissions.
        """
        # SUPER and ADMIN see everything
        if user.is_superuser or user.groups.filter(name="ADMIN").exists():
            return Contract.objects.filter(is_deleted=False)

        # GESTOR sees their own contracts
        if user.groups.filter(name="GESTOR").exists():
            return Contract.objects.filter(is_deleted=False, manager=user)

        # FINANCEIRO and FORNECEDOR see all active contracts (read-only)
        return Contract.objects.filter(is_deleted=False)

    @action(detail=False, methods=["get"])
    def overview(self, request):
        """
        Complete system overview with all key metrics.

        Returns:
        - Contract metrics (total, active, closed, values)
        - Measurement metrics (by status, values)
        - Payment metrics (by status, amounts)
        - Recent activities (last 10 audit logs)
        """
        user = request.user
        contracts_qs = self._get_base_queryset(user)

        # Contract metrics
        contract_stats = contracts_qs.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status=Contract.Status.ACTIVE)),
            closed=Count("id", filter=Q(status=Contract.Status.CLOSED)),
            total_value=Coalesce(Sum("total_value"), Decimal("0.00")),
            total_remaining=Coalesce(
                Sum("remaining_balance"), Decimal("0.00")
            ),
        )

        # Calculate average and percentage
        if contract_stats["total"] > 0:
            avg_value = contract_stats["total_value"] / contract_stats["total"]
        else:
            avg_value = Decimal("0.00")

        # Calculate percentage completed
        if contract_stats["total_value"] > 0:
            paid = (
                contract_stats["total_value"]
                - contract_stats["total_remaining"]
            )
            percentage = (paid / contract_stats["total_value"]) * 100
        else:
            percentage = Decimal("0.00")

        contract_metrics = {
            "total_contracts": contract_stats["total"],
            "active_contracts": contract_stats["active"],
            "closed_contracts": contract_stats["closed"],
            "total_value": contract_stats["total_value"],
            "total_remaining": contract_stats["total_remaining"],
            "avg_contract_value": round(avg_value, 2),
            "percentage_completed": round(percentage, 2),
        }

        # Measurement metrics
        measurements_qs = Measurement.objects.filter(contract__in=contracts_qs)
        measurement_stats = measurements_qs.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=Measurement.Status.PENDING)),
            approved=Count("id", filter=Q(status=Measurement.Status.APPROVED)),
            rejected=Count("id", filter=Q(status=Measurement.Status.REJECTED)),
            total_value=Coalesce(Sum("value"), Decimal("0.00")),
            approved_value=Coalesce(
                Sum("value", filter=Q(status=Measurement.Status.APPROVED)),
                Decimal("0.00"),
            ),
            pending_value=Coalesce(
                Sum("value", filter=Q(status=Measurement.Status.PENDING)),
                Decimal("0.00"),
            ),
        )

        # Calculate average
        if measurement_stats["total"] > 0:
            avg_measurement = (
                measurement_stats["total_value"] / measurement_stats["total"]
            )
        else:
            avg_measurement = Decimal("0.00")

        measurement_metrics = {
            "total_measurements": measurement_stats["total"],
            "pending_measurements": measurement_stats["pending"],
            "approved_measurements": measurement_stats["approved"],
            "rejected_measurements": measurement_stats["rejected"],
            "total_value": measurement_stats["total_value"],
            "approved_value": measurement_stats["approved_value"],
            "pending_value": measurement_stats["pending_value"],
            "avg_measurement_value": round(avg_measurement, 2),
        }

        # Payment metrics
        payments_qs = Payment.objects.filter(contract__in=contracts_qs)
        payment_stats = payments_qs.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=Payment.Status.PENDING)),
            paid=Count("id", filter=Q(status=Payment.Status.PAID)),
            failed=Count("id", filter=Q(status=Payment.Status.FAILED)),
            total_amount=Coalesce(Sum("amount"), Decimal("0.00")),
            paid_amount=Coalesce(
                Sum("amount", filter=Q(status=Payment.Status.PAID)),
                Decimal("0.00"),
            ),
            pending_amount=Coalesce(
                Sum("amount", filter=Q(status=Payment.Status.PENDING)),
                Decimal("0.00"),
            ),
        )

        # Calculate average
        if payment_stats["total"] > 0:
            avg_payment = (
                payment_stats["total_amount"] / payment_stats["total"]
            )
        else:
            avg_payment = Decimal("0.00")

        payment_metrics = {
            "total_payments": payment_stats["total"],
            "pending_payments": payment_stats["pending"],
            "paid_payments": payment_stats["paid"],
            "failed_payments": payment_stats["failed"],
            "total_amount": payment_stats["total_amount"],
            "paid_amount": payment_stats["paid_amount"],
            "pending_amount": payment_stats["pending_amount"],
            "avg_payment_amount": round(avg_payment, 2),
        }

        # Recent activities (last 10)
        recent_logs = AuditLog.objects.select_related("user").order_by(
            "-timestamp"
        )[:10]

        recent_activities = [
            {
                "action": log.action,
                "user": log.user.username if log.user else None,
                "model_name": log.model_name,
                "object_id": log.object_id,
                "object_display": log.object_display,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in recent_logs
        ]

        data = {
            "contracts": contract_metrics,
            "measurements": measurement_metrics,
            "payments": payment_metrics,
            "recent_activities": recent_activities,
        }

        serializer = OverviewSerializer(data)
        return Response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="period",
                description=(
                    "Filter by period: 'month', '6months', or 'year'."
                ),
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="closed_incomplete",
                description=(
                    "When true, include only CLOSED contracts with "
                    "remaining_balance > 0."
                ),
                required=False,
                type=str,
            ),
        ]
    )
    @action(detail=False, methods=["get"])
    def contracts(self, request):
        """
        Contract-specific metrics and statistics.

        Query params:
        - period: 'month', '6months', or 'year'
        - closed_incomplete: 'true' to include only CLOSED contracts
          with remaining_balance > 0
        """
        user = request.user
        contracts_qs = self._get_base_queryset(user)

        period = request.query_params.get("period")
        if period:
            period_days = {
                "month": 30,
                "6months": 180,
                "year": 365,
            }
            days = period_days.get(period)
            if not days:
                return error_response(
                    "Invalid period. Use 'month', '6months', or 'year'.",
                    status.HTTP_400_BAD_REQUEST,
                )
            start_date = timezone.now() - timedelta(days=days)
            contracts_qs = contracts_qs.filter(created_at__gte=start_date)

        closed_incomplete = request.query_params.get("closed_incomplete")
        if closed_incomplete and closed_incomplete.lower() == "true":
            contracts_qs = contracts_qs.filter(
                status=Contract.Status.CLOSED, remaining_balance__gt=0
            )

        stats = contracts_qs.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status=Contract.Status.ACTIVE)),
            closed=Count("id", filter=Q(status=Contract.Status.CLOSED)),
            total_value=Coalesce(Sum("total_value"), Decimal("0.00")),
            total_remaining=Coalesce(
                Sum("remaining_balance"), Decimal("0.00")
            ),
        )

        # Calculate average and percentage
        if stats["total"] > 0:
            avg_value = stats["total_value"] / stats["total"]
        else:
            avg_value = Decimal("0.00")

        if stats["total_value"] > 0:
            paid = stats["total_value"] - stats["total_remaining"]
            percentage = (paid / stats["total_value"]) * 100
        else:
            percentage = Decimal("0.00")

        data = {
            "total_contracts": stats["total"],
            "active_contracts": stats["active"],
            "closed_contracts": stats["closed"],
            "total_value": stats["total_value"],
            "total_remaining": stats["total_remaining"],
            "avg_contract_value": round(avg_value, 2),
            "percentage_completed": round(percentage, 2),
        }

        serializer = ContractMetricsSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def measurements(self, request):
        """
        Measurement-specific metrics.
        """
        user = request.user
        contracts_qs = self._get_base_queryset(user)
        measurements_qs = Measurement.objects.filter(contract__in=contracts_qs)

        stats = measurements_qs.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=Measurement.Status.PENDING)),
            approved=Count("id", filter=Q(status=Measurement.Status.APPROVED)),
            rejected=Count("id", filter=Q(status=Measurement.Status.REJECTED)),
            total_value=Coalesce(Sum("value"), Decimal("0.00")),
            approved_value=Coalesce(
                Sum("value", filter=Q(status=Measurement.Status.APPROVED)),
                Decimal("0.00"),
            ),
            pending_value=Coalesce(
                Sum("value", filter=Q(status=Measurement.Status.PENDING)),
                Decimal("0.00"),
            ),
        )

        # Calculate average
        if stats["total"] > 0:
            avg_value = stats["total_value"] / stats["total"]
        else:
            avg_value = Decimal("0.00")

        data = {
            "total_measurements": stats["total"],
            "pending_measurements": stats["pending"],
            "approved_measurements": stats["approved"],
            "rejected_measurements": stats["rejected"],
            "total_value": stats["total_value"],
            "approved_value": stats["approved_value"],
            "pending_value": stats["pending_value"],
            "avg_measurement_value": round(avg_value, 2),
        }

        serializer = MeasurementMetricsSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def payments(self, request):
        """
        Payment-specific metrics.
        """
        user = request.user
        contracts_qs = self._get_base_queryset(user)
        payments_qs = Payment.objects.filter(contract__in=contracts_qs)

        stats = payments_qs.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=Payment.Status.PENDING)),
            paid=Count("id", filter=Q(status=Payment.Status.PAID)),
            failed=Count("id", filter=Q(status=Payment.Status.FAILED)),
            total_amount=Coalesce(Sum("amount"), Decimal("0.00")),
            paid_amount=Coalesce(
                Sum("amount", filter=Q(status=Payment.Status.PAID)),
                Decimal("0.00"),
            ),
            pending_amount=Coalesce(
                Sum("amount", filter=Q(status=Payment.Status.PENDING)),
                Decimal("0.00"),
            ),
        )

        # Calculate average
        if stats["total"] > 0:
            avg_amount = stats["total_amount"] / stats["total"]
        else:
            avg_amount = Decimal("0.00")

        data = {
            "total_payments": stats["total"],
            "pending_payments": stats["pending"],
            "paid_payments": stats["paid"],
            "failed_payments": stats["failed"],
            "total_amount": stats["total_amount"],
            "paid_amount": stats["paid_amount"],
            "pending_amount": stats["pending_amount"],
            "avg_payment_amount": round(avg_amount, 2),
        }

        serializer = PaymentMetricsSerializer(data)
        return Response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="period",
                description=(
                    "Filter by period: 'month', '6months', or 'year'."
                ),
                required=False,
                type=str,
            )
        ]
    )
    @action(detail=False, methods=["get"])
    def by_manager(self, request):
        """
        Performance metrics grouped by contract manager.

        Returns metrics for each manager:
        - Total contracts managed
        - Active vs closed
        - Total contracted value
        - Completion percentage

        Query params:
        - period: 'month', '6months', or 'year'
        """
        user = request.user
        contracts_qs = self._get_base_queryset(user)

        period = request.query_params.get("period")
        if period:
            period_days = {
                "month": 30,
                "6months": 180,
                "year": 365,
            }
            days = period_days.get(period)
            if not days:
                return error_response(
                    "Invalid period. Use 'month', '6months', or 'year'.",
                    status.HTTP_400_BAD_REQUEST,
                )
            start_date = timezone.now() - timedelta(days=days)
            contracts_qs = contracts_qs.filter(created_at__gte=start_date)

        # Group by manager
        manager_stats = (
            contracts_qs.values(
                "manager__id",
                "manager__username",
                "manager__first_name",
                "manager__last_name",
            )
            .annotate(
                total_contracts=Count("id"),
                active_contracts=Count(
                    "id", filter=Q(status=Contract.Status.ACTIVE)
                ),
                total_value=Coalesce(Sum("total_value"), Decimal("0.00")),
                total_remaining=Coalesce(
                    Sum("remaining_balance"), Decimal("0.00")
                ),
            )
            .order_by("-total_value")
        )

        results = []
        for stat in manager_stats:
            # Build manager name
            manager_name = stat["manager__username"]
            if stat["manager__first_name"] or stat["manager__last_name"]:
                first = stat["manager__first_name"] or ""
                last = stat["manager__last_name"] or ""
                manager_name = f"{first} {last}".strip()

            # Calculate completion percentage
            if stat["total_value"] > 0:
                paid = stat["total_value"] - stat["total_remaining"]
                percentage = (paid / stat["total_value"]) * 100
            else:
                percentage = Decimal("0.00")

            results.append(
                {
                    "manager_id": stat["manager__id"],
                    "manager_name": manager_name,
                    "total_contracts": stat["total_contracts"],
                    "active_contracts": stat["active_contracts"],
                    "total_value": stat["total_value"],
                    "completed_percentage": round(percentage, 2),
                }
            )

        serializer = ManagerPerformanceSerializer(results, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def financial(self, request):
        """
        Detailed financial analysis.

        Returns:
        - Total contracted value
        - Total measured value (approved measurements)
        - Total paid (paid payments)
        - Pending payments
        - Remaining contract balance
        - Measurement to contract ratio
        - Payment to measurement ratio
        - Overall completion percentage
        """
        user = request.user
        contracts_qs = self._get_base_queryset(user)

        # Contract totals
        contract_stats = contracts_qs.aggregate(
            total_contracted=Coalesce(Sum("total_value"), Decimal("0.00")),
            total_remaining=Coalesce(
                Sum("remaining_balance"), Decimal("0.00")
            ),
        )

        # Measurement totals
        measurements_qs = Measurement.objects.filter(contract__in=contracts_qs)
        measurement_stats = measurements_qs.aggregate(
            total_measured=Coalesce(
                Sum("value", filter=Q(status=Measurement.Status.APPROVED)),
                Decimal("0.00"),
            ),
        )

        # Payment totals
        payments_qs = Payment.objects.filter(contract__in=contracts_qs)
        payment_stats = payments_qs.aggregate(
            total_paid=Coalesce(
                Sum("amount", filter=Q(status=Payment.Status.PAID)),
                Decimal("0.00"),
            ),
            total_pending_payments=Coalesce(
                Sum("amount", filter=Q(status=Payment.Status.PENDING)),
                Decimal("0.00"),
            ),
        )

        # Calculate ratios
        total_contracted = contract_stats["total_contracted"]
        total_measured = measurement_stats["total_measured"]
        total_paid = payment_stats["total_paid"]

        measurement_ratio = Decimal("0.00")
        if total_contracted > 0:
            measurement_ratio = (total_measured / total_contracted) * 100

        payment_ratio = Decimal("0.00")
        if total_measured > 0:
            payment_ratio = (total_paid / total_measured) * 100

        overall_completion = Decimal("0.00")
        if total_contracted > 0:
            overall_completion = (total_paid / total_contracted) * 100

        data = {
            "total_contracted": total_contracted,
            "total_measured": total_measured,
            "total_paid": total_paid,
            "total_pending_payments": payment_stats["total_pending_payments"],
            "total_remaining_balance": contract_stats["total_remaining"],
            "measurement_to_contract_ratio": round(measurement_ratio, 2),
            "payment_to_measurement_ratio": round(payment_ratio, 2),
            "overall_completion_percentage": round(overall_completion, 2),
        }

        serializer = FinancialSummarySerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def timeline(self, request):
        """
        Time-series data for trend analysis.

        Query params:
        - period: 'day' (last 30 days) or 'month'
          (last 12 months), default='month'
        - days: number of days to include (for 'day' period), default=30
        - months: number of months to include (for 'month' period), default=12

        Returns timeline data:
        - Contracts created per period
        - Measurements created per period
        - Payments made per period
        - Total amount paid per period
        """
        user = request.user
        contracts_qs = self._get_base_queryset(user)

        period = request.query_params.get("period", "month")

        if period == "day":
            days = int(request.query_params.get("days", 30))
            start_date = timezone.now() - timedelta(days=days)
            trunc_func = TruncDay("created_at")
        else:  # month
            months = int(request.query_params.get("months", 12))
            start_date = timezone.now() - timedelta(days=months * 30)
            trunc_func = TruncMonth("created_at")

        # Contracts timeline
        contract_timeline = (
            contracts_qs.filter(created_at__gte=start_date)
            .annotate(period=trunc_func)
            .values("period")
            .annotate(contracts_created=Count("id"))
            .order_by("period")
        )

        # Measurements timeline
        measurements_qs = Measurement.objects.filter(
            contract__in=contracts_qs, created_at__gte=start_date
        )
        measurement_timeline = (
            measurements_qs.annotate(period=trunc_func)
            .values("period")
            .annotate(measurements_created=Count("id"))
            .order_by("period")
        )

        # Payments timeline
        payments_qs = Payment.objects.filter(
            contract__in=contracts_qs,
            paid_at__gte=start_date,
            status=Payment.Status.PAID,
        )
        if period == "day":
            trunc_paid = TruncDay("paid_at")
        else:
            trunc_paid = TruncMonth("paid_at")
        payment_timeline = (
            payments_qs.annotate(period=trunc_paid)
            .values("period")
            .annotate(
                payments_made=Count("id"),
                total_paid=Coalesce(Sum("amount"), Decimal("0.00")),
            )
            .order_by("period")
        )

        # Merge timelines
        timeline_dict = {}

        for item in contract_timeline:
            if hasattr(item["period"], "date"):
                period_date = item["period"].date()
            else:
                period_date = item["period"]
            timeline_dict[period_date] = {
                "period": period_date,
                "contracts_created": item["contracts_created"],
                "measurements_created": 0,
                "payments_made": 0,
                "total_paid": Decimal("0.00"),
            }

        for item in measurement_timeline:
            if hasattr(item["period"], "date"):
                period_date = item["period"].date()
            else:
                period_date = item["period"]
            if period_date in timeline_dict:
                timeline_dict[period_date]["measurements_created"] = item[
                    "measurements_created"
                ]
            else:
                timeline_dict[period_date] = {
                    "period": period_date,
                    "contracts_created": 0,
                    "measurements_created": item["measurements_created"],
                    "payments_made": 0,
                    "total_paid": Decimal("0.00"),
                }

        for item in payment_timeline:
            if hasattr(item["period"], "date"):
                period_date = item["period"].date()
            else:
                period_date = item["period"]
            if period_date in timeline_dict:
                timeline_dict[period_date]["payments_made"] = item[
                    "payments_made"
                ]
                timeline_dict[period_date]["total_paid"] = item["total_paid"]
            else:
                timeline_dict[period_date] = {
                    "period": period_date,
                    "contracts_created": 0,
                    "measurements_created": 0,
                    "payments_made": item["payments_made"],
                    "total_paid": item["total_paid"],
                }

        results = sorted(timeline_dict.values(), key=lambda x: x["period"])

        serializer = TimelineDataSerializer(results, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def status_distribution(self, request):
        """
        Status distribution for contracts, measurements, and payments.

        Query params:
        - type: 'contracts', 'measurements', or 'payments', default='contracts'

        Returns distribution of records by status with counts and percentages.
        """
        user = request.user
        contracts_qs = self._get_base_queryset(user)

        entity_type = request.query_params.get("type", "contracts")

        if entity_type == "measurements":
            queryset = Measurement.objects.filter(contract__in=contracts_qs)
            status_field = "status"
        elif entity_type == "payments":
            queryset = Payment.objects.filter(contract__in=contracts_qs)
            status_field = "status"
        else:  # contracts
            queryset = contracts_qs
            status_field = "status"

        # Get distribution
        total = queryset.count()
        distribution = (
            queryset.values(status_field)
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        results = []
        for item in distribution:
            percentage = (item["count"] / total * 100) if total > 0 else 0
            results.append(
                {
                    "status": item[status_field],
                    "count": item["count"],
                    "percentage": round(Decimal(percentage), 2),
                }
            )

        serializer = StatusDistributionSerializer(results, many=True)
        return Response(serializer.data)
