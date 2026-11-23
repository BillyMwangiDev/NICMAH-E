from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.parsers import MultiPartParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db import transaction
from django.db.models import Q, Sum, Value, IntegerField
from django.db.models.functions import Coalesce

from users.permissions import IsManagerOrAbove, IsCashierOrAbove

from .models import Category, Product, StockLog, Supplier, PurchaseOrder, PurchaseOrderItem, StockAlert
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductPublicSerializer,
    ProductSearchSuggestionSerializer,
    StockAdjustSerializer,
    StockLogSerializer,
    SupplierSerializer,
    PurchaseOrderSerializer,
    PurchaseOrderCreateSerializer,
    ReceiveItemsSerializer,
    StockAlertSerializer,
)
from .services.excel_import import import_products_from_excel
from .services.excel_export import export_products_to_excel


# ── Public: Product Listing ─────────────────────────────────────────────────

class ProductListView(generics.ListAPIView):
    """Public product catalog with full search and filtering."""
    serializer_class = ProductPublicSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related("category").prefetch_related("additional_images")

        # Exclude admin-only categories for non-staff users
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            qs = qs.filter(category__is_admin_only=False)

        # Category filter
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__slug=category)

        # AI product filter
        is_ai = self.request.query_params.get("is_ai")
        if is_ai is not None:
            qs = qs.filter(is_ai_product=is_ai.lower() == "true")

        # Featured filter
        featured = self.request.query_params.get("featured")
        if featured == "true":
            qs = qs.filter(is_featured=True)

        # Full-text search: name, sku, description, category name
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(sku__icontains=q) |
                Q(description__icontains=q) |
                Q(category__name__icontains=q)
            )

        # Price range filter
        price_min = self.request.query_params.get("price_min")
        price_max = self.request.query_params.get("price_max")
        if price_min:
            try:
                qs = qs.filter(price__gte=float(price_min))
            except ValueError:
                pass
        if price_max:
            try:
                qs = qs.filter(price__lte=float(price_max))
            except ValueError:
                pass

        # Stock filter
        stock = self.request.query_params.get("stock")
        if stock == "in_stock":
            qs = qs.filter(stock_level__gt=0)
        elif stock == "out_of_stock":
            qs = qs.filter(stock_level=0)

        # Sorting
        sort_by = self.request.query_params.get("sort", "name")
        if sort_by == "best_selling":
            qs = qs.annotate(
                qty_sold=Coalesce(
                    Sum(
                        "sale_items__quantity",
                        filter=Q(sale_items__sale__status="completed"),
                    ),
                    Value(0),
                    output_field=IntegerField(),
                )
            ).order_by("-qty_sold", "name")
        else:
            sort_map = {
                "name": "name",
                "name_desc": "-name",
                "price": "price",
                "price_desc": "-price",
                "newest": "-created_at",
                "featured": "-is_featured",
            }
            qs = qs.order_by(sort_map.get(sort_by, "name"))

        # Optional result limit — used by homepage to fetch top-N best sellers
        limit_param = self.request.query_params.get("limit")
        if limit_param:
            try:
                limit = int(limit_param)
                if limit > 0:
                    qs = qs[:limit]
            except ValueError:
                pass

        return qs


class ProductDetailView(generics.RetrieveAPIView):
    """Public single product detail — supports both UUID pk and slug lookup."""
    serializer_class = ProductPublicSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related("category").prefetch_related("additional_images")

    def get_object(self):
        lookup = self.kwargs.get("pk") or self.kwargs.get("slug")
        qs = self.get_queryset()
        # Try UUID first, then slug
        try:
            import uuid as _uuid
            _uuid.UUID(str(lookup))
            return qs.get(pk=lookup)
        except (ValueError, AttributeError):
            return generics.get_object_or_404(qs, slug=lookup)


class ProductSlugDetailView(generics.RetrieveAPIView):
    """Public product detail by slug."""
    serializer_class = ProductPublicSerializer
    permission_classes = [AllowAny]
    queryset = Product.objects.filter(is_active=True).select_related("category").prefetch_related("additional_images")
    lookup_field = "slug"


class FeaturedProductsView(generics.ListAPIView):
    """Public endpoint returning featured products."""
    serializer_class = ProductPublicSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Product.objects.filter(
            is_active=True, is_featured=True
        ).select_related("category").prefetch_related("additional_images")
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            qs = qs.filter(category__is_admin_only=False)
        return qs[:20]


class ProductSearchSuggestionsView(APIView):
    """AJAX search suggestions — returns top 10 matching products as lightweight JSON."""
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response({"suggestions": []})

        qs = Product.objects.filter(
            Q(name__icontains=q) | Q(sku__icontains=q) | Q(category__name__icontains=q),
            is_active=True,
        ).select_related("category")

        if not (request.user.is_authenticated and request.user.is_staff):
            qs = qs.filter(category__is_admin_only=False)

        qs = qs[:10]
        suggestions = [
            {
                "id": str(p.id),
                "name": p.name,
                "slug": p.slug,
                "sku": p.sku,
                "category": p.category.name,
                "price": str(p.price),
                "in_stock": p.stock_level > 0,
            }
            for p in qs
        ]
        return Response({"suggestions": suggestions})


class CategoryListView(generics.ListAPIView):
    """Public category listing — top-level only by default, supports subcategories."""
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Category.objects.filter(is_active=True)
        # Exclude admin-only for non-staff
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            qs = qs.filter(is_admin_only=False)
        # Filter top-level vs all
        top_only = self.request.query_params.get("top_only")
        if top_only == "true":
            qs = qs.filter(parent__isnull=True)
        return qs


class CategoryDetailView(APIView):
    """Public: category detail with its products."""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            category = Category.objects.get(slug=slug, is_active=True)
        except Category.DoesNotExist:
            return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)

        if category.is_admin_only and not (request.user.is_authenticated and request.user.is_staff):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        products_qs = category.products.filter(is_active=True).select_related("category")
        category_data = CategorySerializer(category).data
        products_data = ProductPublicSerializer(products_qs, many=True, context={"request": request}).data

        return Response({
            "category": category_data,
            "products": products_data,
            "product_count": products_qs.count(),
        })


# ── Admin: Inventory Management ─────────────────────────────────────────────

class InventoryAdminListView(generics.ListCreateAPIView):
    """Full inventory with all stock fields — admin only. POST creates a new product."""
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category__slug", "is_ai_product", "is_active", "is_featured"]
    search_fields = ["name", "description", "supplier", "sire_code", "sku"]
    ordering_fields = ["name", "price", "stock_level", "created_at"]
    ordering = ["category", "name"]
    queryset = Product.objects.all().select_related("category").prefetch_related("additional_images")


class StockAdjustView(APIView):
    """PATCH endpoint to adjust stock level of a product. Logs the change in StockLog."""
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = StockAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        adjustment = serializer.validated_data["adjustment"]
        reason_text = serializer.validated_data.get("reason", "")
        new_level = product.stock_level + adjustment

        if new_level < 0:
            return Response(
                {"detail": f"Cannot reduce stock below 0. Current stock: {product.stock_level}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product.stock_level = new_level
        product.save(update_fields=["stock_level"])

        # Record the movement
        StockLog.objects.create(
            product=product,
            change=adjustment,
            reason="restock" if adjustment > 0 else "adjustment",
            note=reason_text,
            user=request.user,
        )

        return Response({
            "id": str(product.id),
            "name": product.name,
            "stock_level": product.stock_level,
            "stock_status": product.stock_status,
        })


# ── Admin: Product Detail / Update / Soft-Delete ────────────────────────────

class ProductAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: GET/PATCH product (supports image upload) + DELETE soft-deletes (is_active=False)."""
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, JSONParser]
    queryset = Product.objects.all().select_related("category").prefetch_related("additional_images")

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        product.is_active = False
        product.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Admin: Stock Movement Log ────────────────────────────────────────────────

class StockLogView(generics.ListAPIView):
    """GET /api/admin/inventory/<uuid>/stock-log/ — last 30 stock movements for a product."""
    serializer_class = StockLogSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return StockLog.objects.filter(
            product_id=self.kwargs["pk"]
        ).select_related("user").order_by("-created_at")[:30]


# ── Admin: Excel Import ─────────────────────────────────────────────────────

class ExcelImportView(APIView):
    """Bulk import products from an Excel (.xlsx) file."""
    permission_classes = [IsManagerOrAbove]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"detail": "No file provided. Send file as multipart/form-data with key 'file'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_name = file_obj.name.lower()
        if not (file_name.endswith(".xlsx") or file_name.endswith(".xls") or file_name.endswith(".csv")):
            return Response(
                {"detail": "Unsupported file type. Please upload .xlsx, .xls, or .csv"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = import_products_from_excel(file_obj)
        return Response(result, status=status.HTTP_200_OK)


# ── Admin: Excel Export ──────────────────────────────────────────────────────

class ExcelExportView(APIView):
    """Download all active products as the standard price-update .xlsx template."""
    permission_classes = [IsManagerOrAbove]

    def get(self, _request):
        from django.http import HttpResponse
        try:
            xlsx_bytes = export_products_to_excel()
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        today = __import__("datetime").date.today().strftime("%Y%m%d")
        response = HttpResponse(
            xlsx_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="nicmah_price_update_{today}.xlsx"'
        return response


# ── Supplier Management ───────────────────────────────────────────────────────

class SupplierListCreateView(generics.ListCreateAPIView):
    """GET/POST suppliers — manager+ only."""
    serializer_class = SupplierSerializer
    permission_classes = [IsManagerOrAbove]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "contact_person", "email", "phone"]
    ordering_fields = ["name", "rating", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        qs = Supplier.objects.all()
        active = self.request.query_params.get("active")
        if active == "true":
            qs = qs.filter(is_active=True)
        elif active == "false":
            qs = qs.filter(is_active=False)
        return qs


class SupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE supplier — manager+ only."""
    serializer_class = SupplierSerializer
    permission_classes = [IsManagerOrAbove]
    queryset = Supplier.objects.all()

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        supplier = self.get_object()
        supplier.is_active = False
        supplier.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Purchase Orders ───────────────────────────────────────────────────────────

class PurchaseOrderListCreateView(generics.ListCreateAPIView):
    """GET/POST purchase orders — manager+ only."""
    permission_classes = [IsManagerOrAbove]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["po_number", "supplier__name", "notes"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at", "expected_delivery", "total"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PurchaseOrderCreateSerializer
        return PurchaseOrderSerializer

    def get_queryset(self):
        return PurchaseOrder.objects.select_related("supplier", "created_by").prefetch_related("items__product")

    def create(self, request, *args, **kwargs):
        serializer = PurchaseOrderCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        po = serializer.save()
        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_201_CREATED)


class PurchaseOrderDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH purchase order — manager+ only."""
    permission_classes = [IsManagerOrAbove]
    queryset = PurchaseOrder.objects.select_related("supplier", "created_by").prefetch_related("items__product")

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return PurchaseOrderCreateSerializer
        return PurchaseOrderSerializer

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


class PurchaseOrderReceiveView(APIView):
    """POST /api/purchase-orders/<uuid>/receive/ — receive items, update stock."""
    permission_classes = [IsManagerOrAbove]

    @transaction.atomic
    def post(self, request, pk):
        try:
            po = PurchaseOrder.objects.select_for_update().prefetch_related("items__product").get(pk=pk)
        except PurchaseOrder.DoesNotExist:
            return Response({"detail": "Purchase order not found."}, status=status.HTTP_404_NOT_FOUND)

        if po.status == "cancelled":
            return Response({"detail": "Cannot receive items on a cancelled PO."}, status=status.HTTP_400_BAD_REQUEST)
        if po.status == "received":
            return Response({"detail": "This PO has already been fully received."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReceiveItemsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items_data = serializer.validated_data["items"]

        errors = []
        updates = []

        for entry in items_data:
            item_id = entry.get("item_id")
            qty = entry.get("quantity_received", 0)
            if qty <= 0:
                continue
            try:
                item = po.items.get(id=item_id)
            except PurchaseOrderItem.DoesNotExist:
                errors.append(f"Item {item_id} not found in this PO.")
                continue
            if item.quantity_received + qty > item.quantity_ordered:
                errors.append(f"Cannot receive more than ordered for {item.product.name}.")
                continue
            updates.append((item, qty))

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        for item, qty in updates:
            item.quantity_received += qty
            item.save(update_fields=["quantity_received"])

            # Update product stock
            product = Product.objects.select_for_update().get(pk=item.product_id)
            product.stock_level += qty
            from django.utils import timezone as tz
            product.last_restocked = tz.now()
            product.save(update_fields=["stock_level", "last_restocked"])

            StockLog.objects.create(
                product=product,
                change=qty,
                reason="purchase_order",
                reference=po.po_number,
                note=f"Received from PO {po.po_number}",
                user=request.user,
            )

        # Update PO status — query fresh from DB to avoid stale prefetch cache
        all_items = PurchaseOrderItem.objects.filter(purchase_order=po)
        all_received = all(i.quantity_received >= i.quantity_ordered for i in all_items)
        any_received = any(i.quantity_received > 0 for i in all_items)
        if all_received:
            po.status = "received"
        elif any_received:
            po.status = "partial"
        po.save(update_fields=["status"])

        return Response(PurchaseOrderSerializer(po).data)


# ── Stock Alerts ──────────────────────────────────────────────────────────────

class StockAlertListView(generics.ListAPIView):
    """GET /api/stock-alerts/ — list alerts, manager+ only."""
    serializer_class = StockAlertSerializer
    permission_classes = [IsManagerOrAbove]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["type", "status", "priority"]
    search_fields = ["product__name", "message"]
    ordering_fields = ["created_at", "priority"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return StockAlert.objects.select_related(
            "product", "acknowledged_by", "resolved_by"
        )


class StockAlertAcknowledgeView(APIView):
    """PATCH /api/stock-alerts/<uuid>/acknowledge/"""
    permission_classes = [IsCashierOrAbove]

    def patch(self, request, pk):
        try:
            alert = StockAlert.objects.get(pk=pk)
        except StockAlert.DoesNotExist:
            return Response({"detail": "Alert not found."}, status=status.HTTP_404_NOT_FOUND)
        if alert.status != "active":
            return Response({"detail": f"Alert is already {alert.status}."}, status=status.HTTP_400_BAD_REQUEST)
        alert.acknowledge(request.user)
        return Response(StockAlertSerializer(alert).data)


class StockAlertResolveView(APIView):
    """PATCH /api/stock-alerts/<uuid>/resolve/"""
    permission_classes = [IsManagerOrAbove]

    def patch(self, request, pk):
        try:
            alert = StockAlert.objects.get(pk=pk)
        except StockAlert.DoesNotExist:
            return Response({"detail": "Alert not found."}, status=status.HTTP_404_NOT_FOUND)
        if alert.status == "resolved":
            return Response({"detail": "Alert is already resolved."}, status=status.HTTP_400_BAD_REQUEST)
        alert.resolve(request.user)
        return Response(StockAlertSerializer(alert).data)


class StockAlertGenerateView(APIView):
    """POST /api/stock-alerts/generate/ — scan all products and create alerts. Admin only."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        from django.utils import timezone
        from .signals import _create_alerts_if_needed, _resolve_stale_alerts
        today = timezone.now().date()
        products = Product.objects.filter(is_active=True)
        count = 0
        for product in products:
            _resolve_stale_alerts(product, today)
            before = StockAlert.objects.filter(product=product, status="active").count()
            _create_alerts_if_needed(product, today)
            after = StockAlert.objects.filter(product=product, status="active").count()
            count += after - before
        return Response({"alerts_created": count, "products_scanned": products.count()})


# ── Purchase Order PDF ────────────────────────────────────────────────────────

class PurchaseOrderPDFView(APIView):
    """GET /api/purchase-orders/<uuid>/pdf/ — download PO as A4 PDF."""
    permission_classes = [IsManagerOrAbove]

    def get(self, request, pk):
        try:
            po = PurchaseOrder.objects.select_related("supplier", "created_by").prefetch_related("items__product").get(pk=pk)
        except PurchaseOrder.DoesNotExist:
            return Response({"detail": "Purchase order not found."}, status=status.HTTP_404_NOT_FOUND)

        from .services.po_pdf import generate_po_pdf
        from django.http import HttpResponse
        pdf_bytes = generate_po_pdf(po)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{po.po_number}.pdf"'
        return response
