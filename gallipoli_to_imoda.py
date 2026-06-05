#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gallipoli (Ticimax) XML feed -> Imoda XML format dönüştürücü.
Kaynak URL'den çeker; yerel gallipoliunderwear.xml dosyası kullanılmaz.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import Request, urlopen

DEFAULT_SOURCE_URL = (
    "https://gallipoliunderwear.com/TicimaxXmlV2/C512FF7F5C4B400D879CF5B8512C4D02/"
)

# Ozellik adları -> Imoda variant alan adları
ATTR_LABELS = {
    "RENK": "Renk",
    "BEDEN": "Beden",
    "NUMARA": "Numara",
    "BOY": "Boy",
    "EBAT": "Ebat",
}


def fetch_xml(url: str, timeout: int = 120) -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/xml,text/xml,*/*",
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def text(elem: ET.Element | None, default: str = "") -> str:
    if elem is None or elem.text is None:
        return default
    return elem.text.strip()


def parse_category_tree(tree: str) -> tuple[str, str, str, str]:
    parts = [p.strip() for p in tree.split("/") if p.strip()]
    if not parts:
        return "", "", "", ""
    main = parts[0]
    top = parts[1] if len(parts) > 1 else parts[0]
    sub = parts[-1]
    category = " >>> ".join(parts)
    return main, top, sub, category


def extract_product_code(urun_adi: str, stok_kodu: str) -> str:
    m = re.search(r"\(([^)]+)\)\s*$", urun_adi)
    if m:
        return m.group(1).strip()
    if "-" in stok_kodu:
        return stok_kodu.rsplit("-", 1)[0]
    return stok_kodu


def build_description(on_yazi: str, aciklama: str) -> str:
    """Ham HTML; XML yazılırken ElementTree otomatik kaçış uygular."""
    parts = []
    if on_yazi:
        parts.append(on_yazi)
    if aciklama:
        parts.append(aciklama)
    return "".join(parts)


def capitalize_attr(name: str) -> str:
    key = name.strip().upper()
    if key in ATTR_LABELS:
        return ATTR_LABELS[key]
    return name.strip().title()


def parse_ozellikler(secenek: ET.Element) -> list[tuple[str, str]]:
    props: list[tuple[str, str]] = []
    ek = secenek.find("EkSecenekOzellik")
    if ek is None:
        return props
    for oz in ek.findall("Ozellik"):
        tanim = oz.get("Tanim") or text(oz)
        deger = oz.get("Deger") or text(oz)
        if tanim and deger:
            props.append((capitalize_attr(tanim), deger))
    return props


def add_child(parent: ET.Element, tag: str, value: str | int | float) -> ET.Element:
    child = ET.SubElement(parent, tag)
    child.text = str(value)
    return child


def convert_urun(urun: ET.Element, index: int) -> ET.Element | None:
    secenekler = list(urun.findall("./UrunSecenek/Secenek"))
    if not secenekler:
        return None

    first = secenekler[0]
    urun_karti_id = text(urun.find("UrunKartiID"))
    urun_adi = text(urun.find("UrunAdi"))
    stok_kodu = text(first.find("StokKodu"))

    product = ET.Element("product")

    add_child(product, "id", f"gp{urun_karti_id or index}")
    add_child(product, "productCode", extract_product_code(urun_adi, stok_kodu))
    add_child(product, "barcode", "")

    kategori_tree = text(urun.find("KategoriTree"))
    main_cat, top_cat, sub_cat, category = parse_category_tree(kategori_tree)
    kategori = text(urun.find("Kategori"))

    add_child(product, "main_category", main_cat)
    add_child(product, "top_category", top_cat or kategori)
    add_child(product, "sub_category", sub_cat or kategori)
    add_child(product, "sub_category_", "")
    add_child(product, "categoryID", text(urun.find("KategoriID")))
    add_child(product, "category", category or kategori)

    aktif = text(urun.find("Aktif")).lower()
    add_child(product, "active", "1" if aktif in ("evet", "1", "true") else "0")

    add_child(product, "brandID", text(urun.find("MarkaID")))
    add_child(product, "brand", text(urun.find("Marka")))
    add_child(product, "name", urun_adi)

    on_yazi = text(urun.find("OnYazi"))
    aciklama = text(urun.find("Aciklama"))
    add_child(product, "description", build_description(on_yazi, aciklama))

    variants_el = ET.SubElement(product, "variants")
    total_qty = 0

    for secenek in secenekler:
        sec_aktif = text(secenek.find("Aktif")).lower()
        if sec_aktif not in ("evet", "1", "true"):
            continue

        props = parse_ozellikler(secenek)
        variant = ET.SubElement(variants_el, "variant")

        if len(props) >= 1:
            add_child(variant, "name1", props[0][0])
            add_child(variant, "value1", props[0][1])
        else:
            add_child(variant, "name1", "")
            add_child(variant, "value1", "")

        if len(props) >= 2:
            add_child(variant, "name2", props[1][0])
            add_child(variant, "value2", props[1][1])
        else:
            add_child(variant, "name2", "")
            add_child(variant, "value2", "")

        qty = int(float(text(secenek.find("StokAdedi"), "0") or "0"))
        total_qty += qty
        add_child(variant, "quantity", qty)
        add_child(variant, "barcode", text(secenek.find("Barkod")))

    resimler = urun.find("Resimler")
    if resimler is not None:
        for i, resim in enumerate(resimler.findall("Resim"), start=1):
            url = text(resim)
            if url:
                add_child(product, f"image{i}", url)

    satis = text(first.find("SatisFiyati"), "0")
    indirimli = text(first.find("IndirimliFiyat"), satis)
    kdv = text(first.find("KdvOrani"), "10")

    try:
        tax = float(kdv) / 100.0
    except ValueError:
        tax = 0.1

    add_child(product, "listPrice", satis)
    add_child(product, "price", indirimli or satis)
    add_child(product, "tax", tax)
    add_child(product, "currency", text(first.find("ParaBirimiKodu"), "TRY") or "TRY")
    add_child(product, "desi", text(first.find("Desi"), "1") or "1")
    add_child(product, "quantity", total_qty)

    return product


def convert_feed(root: ET.Element) -> ET.Element:
    products_root = ET.Element("products")

    urunler = root.find("Urunler")
    if urunler is None:
        return products_root

    for i, urun in enumerate(urunler.findall("Urun"), start=1):
        product = convert_urun(urun, i)
        if product is not None:
            products_root.append(product)

    return products_root


def write_imoda_xml(products_root: ET.Element, output_path: Path) -> None:
    tree = ET.ElementTree(products_root)
    ET.indent(tree, space="  ")

    with output_path.open("wb") as f:
        f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gallipoli Ticimax XML -> Imoda format dönüştürücü"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_SOURCE_URL,
        help="Gallipoli XML feed URL",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="gallipoli_imoda.xml",
        help="Çıktı dosyası (varsayılan: gallipoli_imoda.xml)",
    )
    parser.add_argument(
        "--only-active",
        action="store_true",
        help="Sadece Aktif=Evet ürünleri dahil et",
    )
    args = parser.parse_args()

    print(f"XML indiriliyor: {args.url}")
    raw = fetch_xml(args.url)
    root = ET.fromstring(raw)

    if args.only_active:
        urunler = root.find("Urunler")
        if urunler is not None:
            for urun in list(urunler.findall("Urun")):
                if text(urun.find("Aktif")).lower() != "evet":
                    urunler.remove(urun)

    products = convert_feed(root)
    count = len(products.findall("product"))
    output = Path(args.output)
    write_imoda_xml(products, output)

    print(f"Tamamlandı: {count} ürün -> {output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
