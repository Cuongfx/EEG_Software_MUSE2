from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


HEADERS = ["Name", "ID", "Age", "score", "Note"]
SHEET_NAME = "Master Control"
XML_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"


def append_master_control_row(path: Path, row: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = read_master_control_rows(path)
    rows.append([str(value) for value in row])
    write_master_control_rows(path, rows)


def read_master_control_rows(path: Path) -> list[list[str]]:
    if not path.exists():
        return [HEADERS.copy()]

    try:
        with ZipFile(path, "r") as archive:
            sheet_xml = archive.read("xl/worksheets/sheet1.xml")
            shared_strings = _read_shared_strings(archive)
    except Exception:
        return [HEADERS.copy()]

    root = ET.fromstring(sheet_xml)
    rows: list[list[str]] = []
    sheet_data = root.find(_qn("sheetData"))
    if sheet_data is None:
        return [HEADERS.copy()]

    for row_elem in sheet_data.findall(_qn("row")):
        row_values = [""] * len(HEADERS)
        for cell in row_elem.findall(_qn("c")):
            cell_ref = cell.attrib.get("r", "A1")
            column_index = _column_index_from_ref(cell_ref)
            if not 0 <= column_index < len(HEADERS):
                continue
            value = ""
            cell_type = cell.attrib.get("t")
            if cell_type == "inlineStr":
                text_parts = [node.text or "" for node in cell.findall(f".//{_qn('t')}")]
                value = "".join(text_parts)
            elif cell_type == "s":
                value_node = cell.find(_qn("v"))
                if value_node is not None and value_node.text is not None:
                    index = int(value_node.text)
                    if 0 <= index < len(shared_strings):
                        value = shared_strings[index]
            else:
                value_node = cell.find(_qn("v"))
                value = value_node.text if value_node is not None and value_node.text is not None else ""
            row_values[column_index] = value
        if any(value != "" for value in row_values):
            rows.append(row_values)

    if not rows:
        return [HEADERS.copy()]
    if rows[0] != HEADERS:
        rows.insert(0, HEADERS.copy())
    return rows


def write_master_control_rows(path: Path, rows: list[list[str]]) -> None:
    workbook = _build_workbook_xml()
    worksheet = _build_worksheet_xml(rows)
    workbook_rels = _build_workbook_rels_xml()
    root_rels = _build_root_rels_xml()
    content_types = _build_content_types_xml()
    styles = _build_styles_xml()

    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/styles.xml", styles)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)


def _build_workbook_xml() -> bytes:
    workbook = ET.Element(
        "workbook",
        {
            "xmlns": XML_NS,
            "xmlns:r": REL_NS,
        },
    )
    sheets = ET.SubElement(workbook, "sheets")
    ET.SubElement(
        sheets,
        "sheet",
        {
            "name": SHEET_NAME,
            "sheetId": "1",
            f"{{{REL_NS}}}id": "rId1",
        },
    )
    return ET.tostring(workbook, encoding="utf-8", xml_declaration=True)


def _build_worksheet_xml(rows: list[list[str]]) -> bytes:
    worksheet = ET.Element("worksheet", {"xmlns": XML_NS})
    if rows:
        ET.SubElement(worksheet, "dimension", {"ref": f"A1:E{len(rows)}"})
    sheet_data = ET.SubElement(worksheet, "sheetData")

    for row_index, row_values in enumerate(rows, start=1):
        row_elem = ET.SubElement(sheet_data, "row", {"r": str(row_index)})
        for column_index, value in enumerate(row_values[: len(HEADERS)], start=1):
            cell_ref = f"{_column_letter(column_index)}{row_index}"
            cell = ET.SubElement(row_elem, "c", {"r": cell_ref})
            if _is_number(value):
                value_elem = ET.SubElement(cell, "v")
                value_elem.text = str(value)
            else:
                cell.attrib["t"] = "inlineStr"
                inline = ET.SubElement(cell, "is")
                text = ET.SubElement(inline, "t")
                text.text = str(value)

    return ET.tostring(worksheet, encoding="utf-8", xml_declaration=True)


def _build_workbook_rels_xml() -> bytes:
    relationships = ET.Element("Relationships", {"xmlns": PKG_REL_NS})
    ET.SubElement(
        relationships,
        "Relationship",
        {
            "Id": "rId1",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
            "Target": "worksheets/sheet1.xml",
        },
    )
    ET.SubElement(
        relationships,
        "Relationship",
        {
            "Id": "rId2",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles",
            "Target": "styles.xml",
        },
    )
    return ET.tostring(relationships, encoding="utf-8", xml_declaration=True)


def _build_root_rels_xml() -> bytes:
    relationships = ET.Element("Relationships", {"xmlns": PKG_REL_NS})
    ET.SubElement(
        relationships,
        "Relationship",
        {
            "Id": "rId1",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
            "Target": "xl/workbook.xml",
        },
    )
    return ET.tostring(relationships, encoding="utf-8", xml_declaration=True)


def _build_content_types_xml() -> bytes:
    types = ET.Element("Types", {"xmlns": CONTENT_NS})
    ET.SubElement(
        types,
        "Default",
        {
            "Extension": "rels",
            "ContentType": "application/vnd.openxmlformats-package.relationships+xml",
        },
    )
    ET.SubElement(
        types,
        "Default",
        {
            "Extension": "xml",
            "ContentType": "application/xml",
        },
    )
    ET.SubElement(
        types,
        "Override",
        {
            "PartName": "/xl/workbook.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
        },
    )
    ET.SubElement(
        types,
        "Override",
        {
            "PartName": "/xl/worksheets/sheet1.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
        },
    )
    ET.SubElement(
        types,
        "Override",
        {
            "PartName": "/xl/styles.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml",
        },
    )
    return ET.tostring(types, encoding="utf-8", xml_declaration=True)


def _build_styles_xml() -> bytes:
    style_sheet = ET.Element("styleSheet", {"xmlns": XML_NS})
    fonts = ET.SubElement(style_sheet, "fonts", {"count": "1"})
    font = ET.SubElement(fonts, "font")
    ET.SubElement(font, "sz", {"val": "11"})
    ET.SubElement(font, "name", {"val": "Calibri"})

    fills = ET.SubElement(style_sheet, "fills", {"count": "2"})
    ET.SubElement(ET.SubElement(fills, "fill"), "patternFill", {"patternType": "none"})
    ET.SubElement(ET.SubElement(fills, "fill"), "patternFill", {"patternType": "gray125"})

    borders = ET.SubElement(style_sheet, "borders", {"count": "1"})
    border = ET.SubElement(borders, "border")
    ET.SubElement(border, "left")
    ET.SubElement(border, "right")
    ET.SubElement(border, "top")
    ET.SubElement(border, "bottom")
    ET.SubElement(border, "diagonal")

    cell_style_xfs = ET.SubElement(style_sheet, "cellStyleXfs", {"count": "1"})
    ET.SubElement(cell_style_xfs, "xf", {"numFmtId": "0", "fontId": "0", "fillId": "0", "borderId": "0"})
    cell_xfs = ET.SubElement(style_sheet, "cellXfs", {"count": "1"})
    ET.SubElement(
        cell_xfs,
        "xf",
        {
            "numFmtId": "0",
            "fontId": "0",
            "fillId": "0",
            "borderId": "0",
            "xfId": "0",
        },
    )
    cell_styles = ET.SubElement(style_sheet, "cellStyles", {"count": "1"})
    ET.SubElement(cell_styles, "cellStyle", {"name": "Normal", "xfId": "0", "builtinId": "0"})
    return ET.tostring(style_sheet, encoding="utf-8", xml_declaration=True)


def _read_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall(_qn("si")):
        text_parts = [node.text or "" for node in item.findall(f".//{_qn('t')}")]
        strings.append("".join(text_parts))
    return strings


def _column_letter(index: int) -> str:
    result = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _column_index_from_ref(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha())
    result = 0
    for char in letters:
        result = result * 26 + (ord(char.upper()) - 64)
    return max(result - 1, 0)


def _qn(tag: str) -> str:
    return f"{{{XML_NS}}}{tag}"


def _is_number(value: str) -> bool:
    text = str(value).strip()
    if not text:
        return False
    try:
        float(text)
    except ValueError:
        return False
    return True
