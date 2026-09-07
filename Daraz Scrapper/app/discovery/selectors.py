"""Centralized CSS and DOM selectors for Daraz Pakistan marketplace discovery.

Inspired by and adapted from reference implementations:
- sushil-rgb/Daraz-Global-WebScraper (selectors.yaml)
- MuhammadAhmedSuhail/WebScraping-Ecommerce-Website (Scrape.ipynb)
"""

from typing import List


class DarazSelectors:
    """Centralized selector definitions for category trees, product catalog cards, and pagination."""

    # Category Menu & Navigation
    CATEGORY_MENU_ROOT: List[str] = [
        "ul.lzd-site-menu-root",
        "div.lzd-site-menu-nav-category",
        ".menu-labels",
        "#J_menu_wrapper",
        "div[data-spm='cate_menu']",
        "ul[data-spm^='cate_']",
    ]

    CATEGORY_ROOT_ITEMS: List[str] = [
        "ul.lzd-site-menu-root > li.lzd-site-menu-root-item",
        ".menu-labels > li",
        ".lzd-site-menu-nav-category li.level-1",
        "li.lzd-site-menu-root-item",
    ]

    CATEGORY_SUB_ITEMS: List[str] = [
        "ul.lzd-site-menu-sub-item > li",
        ".lzd-site-menu-sub-item",
        "li.level-2",
        "li.lzd-site-menu-grand-item",
        ".sub-item",
    ]

    CATEGORY_LINKS_FALLBACK: List[str] = [
        "a[href*='/category/']",
        "a[href*='-category/']",
        ".category-item a",
        "a[href*='/shop/']",
    ]

    # Product Cards & Grid Items
    PRODUCT_CARDS: List[str] = [
        "div[data-qa-locator='product-item']",
        "div.gridItem--Yd0sa",
        "div.box--ujueT",
        "div.Bm3ON",
        "div[data-item-id]",
        "div.c2prKC",
        "div.c3Keof",
        "div.ant-card",
    ]

    PRODUCT_LINKS: List[str] = [
        "div.mainPic--ehOdr a",
        "a[data-qa-locator='product-item']",
        "div.title--wFj93 a",
        "a.product-card--vHfY9",
        "div.image-wrapper a",
        "a[href*='-i']",
        "a[href*='daraz.pk/products/']",
    ]

    PRODUCT_TITLES: List[str] = [
        "div.title--wFj93",
        "div#id-title",
        ".title--title--wFj93",
        "a[title]",
        ".product-title",
    ]

    # Pagination Elements
    PAGINATION_CONTAINERS: List[str] = [
        "ul.ant-pagination",
        "div.pager",
        "div.pagination-container",
        "ul.pager",
    ]

    NEXT_PAGE_BUTTONS: List[str] = [
        "li.ant-pagination-next:not(.ant-pagination-disabled) a",
        "li[title='Next Page']:not(.ant-pagination-disabled) a",
        "li.ant-pagination-next a",
        "a.pager-next",
        "li[title='Next Page']",
        "a[title='Next Page']",
    ]

    PAGINATION_ITEMS: List[str] = [
        "li.ant-pagination-item",
        "li.pager-item",
        "li[tabindex='0']",
    ]

    ACTIVE_PAGE_ITEM: List[str] = [
        "li.ant-pagination-item-active",
        "li.pager-current",
        "li.active",
    ]
