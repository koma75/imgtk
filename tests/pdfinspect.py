"""PDF introspection helpers: parse a generated PDF's object graph and assert on
page order, geometry, embedded images, outline, and catalog viewer keys.
"""
from __future__ import annotations

import re

from .fixtures import JOIN_SIZES


def pdf_objects(data):
    return {int(m.group(1)): m.group(2) for m in re.finditer(rb"(?m)^(\d+)\s+0\s+obj\b(.*?)endobj", data, re.S)}


def pdf_page_order(data):
    objs = pdf_objects(data)
    node = None
    for body in objs.values():
        if re.search(rb"/Type\s*/Pages\b", body):
            node = body
            break
    if node is None:
        raise AssertionError("PDF has no /Type /Pages node")
    kids = re.search(rb"/Kids\s*\[([^\]]*)\]", node)
    if kids is None:
        raise AssertionError("PDF /Pages node has no /Kids array")
    return objs, [int(n) for n in re.findall(rb"(\d+)\s+0\s+R", kids.group(1))]


def pdf_pages(data):
    objs, order = pdf_page_order(data)
    out = []
    for num in order:
        body = objs[num]
        box = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", body)
        if box is None:
            raise AssertionError("page object {0} has no MediaBox".format(num))
        w, h = float(box.group(3)), float(box.group(4))
        sizes = []
        res = re.search(rb"/Resources\s*(\d+)\s+0\s+R", body)
        if res:
            xobj = re.search(rb"/XObject\s*<<([^>]*)>>", objs[int(res.group(1))], re.S)
            if xobj:
                for ref in re.findall(rb"(\d+)\s+0\s+R", xobj.group(1)):
                    img = objs[int(ref)]
                    mw = re.search(rb"/Width\s+(\d+)", img)
                    mh = re.search(rb"/Height\s+(\d+)", img)
                    if mw and mh:
                        sizes.append((int(mw.group(1)), int(mh.group(1))))
        out.append((w, h, sizes))
    return out


def pdf_outlines(data):
    objs, order = pdf_page_order(data)
    index = {num: i + 1 for i, num in enumerate(order)}
    out = {}
    for body in objs.values():
        title = re.search(rb"/Title\s*\(([^)]*)\)", body)
        dest = re.search(rb"/Dest\s*\[\s*(\d+)\s+0\s+R", body)
        if title and dest:
            out[title.group(1).decode()] = index.get(int(dest.group(1)), -1)
    return out


def pdf_catalog(data):
    objs = pdf_objects(data)
    for body in objs.values():
        if re.search(rb"/Type\s*/Catalog\b", body):
            return body
    raise AssertionError("PDF has no /Type /Catalog object")


def pdf_page_layout(data):
    """/PageLayout name in the document catalog (PDF32000 Table 3.2), or None."""
    m = re.search(rb"/PageLayout\s*/([A-Za-z]+)", pdf_catalog(data))
    return m.group(1).decode() if m else None


def pdf_direction(data):
    """/Direction name in the catalog ViewerPreferences (PDF32000 Table 3.22), or None."""
    prefs = re.search(rb"/ViewerPreferences\s*<<(.*?)>>", pdf_catalog(data), re.S)
    if prefs is None:
        return None
    direction = re.search(rb"/Direction\s*/([A-Za-z0-9]+)", prefs.group(1))
    return direction.group(1).decode() if direction else None


def pdf_page_mode(data):
    """/PageMode name in the document catalog (PDF32000 Table 3.2), or None."""
    m = re.search(rb"/PageMode\s*/([A-Za-z0-9]+)", pdf_catalog(data))
    return m.group(1).decode() if m else None


def pdf_open_action(data):
    """The /OpenAction in the document catalog as a compact summary string.

    Returns a string like ``"page=1,fit=FitH"`` or ``"page=1,xyz,zoom=1.5"``
    for an explicit array, or ``"none"`` when the entry is not present.  The
    catalog /OpenAction is either an inline array ``[page /Fit null]`` (which
    fpdf writes by default) or, after our join writes it, a Go To dictionary
    ``<</D [page /Loc ...] /S /GoTo>>``.
    """
    cat = pdf_catalog(data)
    m = re.search(rb"/OpenAction\s*(\[|<<)", cat)
    if not m:
        return "none"
    tail = cat[m.end():]
    kind = m.group(1).decode()
    fit = re.search(rb"/(Fit|FitH|FitV|FitB|FitBH|FitBV)\b", tail)
    xyz = re.search(rb"/XYZ\s+null\s+null\s+([0-9.]+|null)", tail)
    if fit:
        return "page=1,fit={0}".format(fit.group(1).decode())
    if xyz:
        z = xyz.group(1).decode()
        return "page=1,xyz,zoom={0}".format(z)
    return "page=1,other"


def pdf_check(data):
    if not data.startswith(b"%PDF-"):
        raise AssertionError("output is not a PDF (missing %PDF- header)")
    if b"%%EOF" not in data[-1024:]:
        raise AssertionError("PDF is truncated (missing %%EOF trailer)")
    return data


def expect_pdf(work, pdf_name, expected_names, dpi, label):
    data = pdf_check((work / pdf_name).read_bytes())
    pages = pdf_pages(data)
    if len(pages) != len(expected_names):
        raise AssertionError(
            "{0}: PDF has {1} pages, expected {2} ({3})".format(
                label, len(pages), len(expected_names), ", ".join(expected_names)
            )
        )
    for i, name in enumerate(expected_names, 1):
        got_w, got_h, sizes = pages[i - 1]
        want_w, want_h = JOIN_SIZES[name]
        for got, want_px, unit in ((got_w, want_w, "width"), (got_h, want_h, "height")):
            want_pt = want_px * 72.0 / dpi
            if abs(got - want_pt) > 0.05:
                raise AssertionError(
                    "{0}: page {1} {2} MediaBox is {3}pt, expected {4:.2f}pt ({5}px at {6}dpi)".format(
                        label, i, unit, got, want_pt, want_px, dpi
                    )
                )
        if len(sizes) != 1:
            raise AssertionError("{0}: page {1} embeds {2} images (expected 1)".format(label, i, len(sizes)))
        if sizes[0] != (want_w, want_h):
            raise AssertionError(
                "{0}: page {1} embeds a {2}x{3}px image, expected {4}x{5}px for {6}".format(
                    label, i, sizes[0][0], sizes[0][1], want_w, want_h, name
                )
            )
    return data


def expect_pdf_toc(data, toc_entries, label):
    outlines = pdf_outlines(data)
    for pagenum, level, title in toc_entries:
        if title not in outlines:
            raise AssertionError("{0}: PDF outline is missing entry {1!r}".format(label, title))
        if outlines[title] != pagenum:
            raise AssertionError(
                "{0}: outline entry {1!r} points at page {2} (expected {3})".format(label, title, outlines[title], pagenum)
            )
    return outlines
