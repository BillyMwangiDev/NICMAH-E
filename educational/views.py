from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
import math
import re
from .models import Article


def _estimate_minutes_from_html(html: str) -> int:
    """Rudimentary reading time estimator (200 wpm)."""
    # Strip HTML tags to count words more accurately
    text = re.sub(r"<[^>]+>", " ", html or "")
    words = len([w for w in text.split() if w])
    return max(1, math.ceil(words / 200))


def article_list(request):
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("cat", "").strip()
    base_qs = Article.objects.filter(is_published=True)
    if q:
        base_qs = base_qs.filter(title__icontains=q) | base_qs.filter(excerpt__icontains=q) | base_qs.filter(
            content__icontains=q
        )
    if cat:
        base_qs = base_qs.filter(category__iexact=cat)

    articles_qs = base_qs.order_by("-published_at", "-created_at")
    paginator = Paginator(articles_qs, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    # Attach lightweight reading time
    for a in page_obj.object_list:
        try:
            a.reading_minutes = _estimate_minutes_from_html(a.content or a.excerpt)
        except Exception:
            a.reading_minutes = 1

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        # Return partial HTML for infinite scrolling
        html = render(request, "educational/_article_cards.html", {"articles": page_obj.object_list}).content.decode("utf-8")
        return JsonResponse({
            "html": html,
            "has_next": page_obj.has_next(),
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
        })

    # Distinct categories for chips (from published articles)
    categories = (
        Article.objects.filter(is_published=True)
        .exclude(category="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    # Featured post (top of first page, not in AJAX requests)
    featured = None
    if not page_number and page_obj.object_list:
        featured = page_obj.object_list[0]

    context = {
        "page_obj": page_obj,
        "articles": page_obj.object_list,
        "featured": featured,
        "q": q,
        "active_cat": cat,
        "categories": categories,
    }
    return render(request, "educational/article_list.html", context)


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
    return render(request, "educational/article_detail.html", {"article": article})
