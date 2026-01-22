# https://chatgpt.com/c/696c9403-3984-8332-a05c-d3b9d7fe982d

import streamlit as st
import pandas as pd
import re
from io import StringIO

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="🧾 Markdown → CSV Parser",
    layout="wide"
)

st.title("🧾 Robust Markdown Table Parser")
st.caption("Parse complex ESG markdown tables into structured CSV")

# =========================================================
# INPUT
# =========================================================

markdown_text = st.text_area(
    "📋 Paste Markdown Table Here",
    height=450
)

# =========================================================
# UTILITIES
# =========================================================

def is_table_row_start(line: str) -> bool:
    """
    Detect a logical table row.
    """
    return line.strip().startswith("|") and line.count("|") >= 4


def clean_cell(text):
    """
    Normalize multiline cell safely.
    """
    if text is None or pd.isna(text):
        return ""

    text = str(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def normalize_sdg(raw):
    """
    Supports:
      '3 GOOD HEALTH AND WELL-GEING'
      '3\\nGOOD HEALTH\\nAND WELL-GOING'
    """
    if raw is None or pd.isna(raw):
        return None, None

    raw = str(raw)
    raw = raw.replace("\n", " ")
    raw = re.sub(r"\s+", " ", raw).strip()

    if raw == "":
        return None, None

    # Extract SDG number
    num_match = re.search(r"\d+", raw)
    sdg_number = num_match.group(0) if num_match else None

    # Remove number from name
    sdg_name = raw.replace(sdg_number or "", "").strip().title()

    return sdg_number, sdg_name


# =========================================================
# CORE PARSER
# =========================================================

def reconstruct_rows(md_text: str):
    """
    Merge wrapped markdown rows into logical rows.
    """
    lines = [l.rstrip() for l in md_text.splitlines() if l.strip()]

    logical_rows = []
    buffer = ""

    for line in lines:
        if is_table_row_start(line):
            if buffer:
                logical_rows.append(buffer)
            buffer = line
        else:
            buffer += " " + line.strip()

    if buffer:
        logical_rows.append(buffer)

    # Remove header separators
    logical_rows = [
        row for row in logical_rows
        if not re.match(r"^\|\s*-+", row)
    ]

    return logical_rows


def parse_markdown_table(md_text: str) -> pd.DataFrame:
    rows = reconstruct_rows(md_text)

    parsed = []
    header = None
    expected_cols = None

    for idx, row in enumerate(rows):
        parts = [p.strip() for p in row.strip("|").split("|")]

        # Header
        if idx == 0:
            header = parts
            expected_cols = len(header)
            parsed.append(parts)
            continue

        # Fix column explosion
        if len(parts) > expected_cols:
            # Merge everything between Target and Unit into disclosure
            head = parts[:2]
            tail = parts[-2:]
            middle = parts[2:-2]
            merged_disclosure = " | ".join(middle)
            parts = head + [merged_disclosure] + tail

        elif len(parts) < expected_cols:
            parts = parts + [""] * (expected_cols - len(parts))

        parsed.append(parts)

    df = pd.DataFrame(parsed[1:], columns=header)

    # -----------------------
    # Clean cells
    # -----------------------
    for col in df.columns:
        df[col] = df[col].apply(clean_cell)

    # -----------------------
    # Forward-fill SDG
    # -----------------------
    if "SDG" in df.columns:
        df["SDG"] = df["SDG"].replace("", pd.NA).ffill()

        normalized = df["SDG"].apply(normalize_sdg)
        df["SDG_Number"] = normalized.apply(lambda x: x[0])
        df["SDG_Name"] = normalized.apply(lambda x: x[1])

    # -----------------------
    # Column ordering
    # -----------------------
    preferred = [
        "SDG_Number",
        "SDG_Name",
        "Target",
        "Available Business Disclosures",
        "Unit",
        "Sources",
    ]

    ordered = [c for c in preferred if c in df.columns]
    remaining = [c for c in df.columns if c not in ordered]

    df = df[ordered + remaining]

    return df


# =========================================================
# UI
# =========================================================

if st.button("🚀 Parse Markdown"):
    try:
        df = parse_markdown_table(markdown_text)

        st.success("✅ Markdown parsed successfully")

        st.subheader("📊 Parsed Table")
        st.dataframe(df, use_container_width=True)

        # Export CSV
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)

        st.download_button(
            "⬇️ Download CSV",
            csv_buffer.getvalue(),
            file_name="sdg_parsed.csv",
            mime="text/csv"
        )

        with st.expander("ℹ️ Dataset Info"):
            st.write("Rows:", len(df))
            st.write("Columns:", df.columns.tolist())

    except Exception as e:
        st.error(f"❌ Parsing failed: {e}")


# import streamlit as st
# import pandas as pd
# import re
# from io import StringIO

# # =========================================================
# # PAGE CONFIG
# # =========================================================

# st.set_page_config(
#     page_title="🧾 PDF Markdown → CSV Parser",
#     layout="wide"
# )

# st.title("🧾 PDF Table Markdown Parser")
# st.caption("Robust parser for complex multi-line PDF extracted markdown tables")

# # =========================================================
# # INPUT
# # =========================================================

# markdown_text = st.text_area(
#     "📋 Paste Markdown Table Here",
#     height=420
# )

# # =========================================================
# # UTILITIES
# # =========================================================
# def is_table_row_start(line: str) -> bool:
#     """
#     A real table row starts with | and contains multiple pipe separators.
#     """
#     return line.strip().startswith("|") and line.count("|") >= 4


# def clean_cell(text):
#     """
#     Preserve bullets and normalize spacing safely.
#     """
#     if text is None or pd.isna(text):
#         return ""

#     text = str(text)
#     text = text.replace("\r\n", "\n").replace("\r", "\n")
#     text = re.sub(r"\n{3,}", "\n\n", text)

#     lines = [line.strip() for line in text.split("\n")]
#     return "\n".join(lines).strip()


# def normalize_sdg(raw):
#     """
#     Normalize SDG safely:
#         3
#         GOOD HEALTH
#         AND WELL-BEING
#     →
#         SDG_Number = 3
#         SDG_Name = Good Health And Well-Being
#     """
#     if raw is None or pd.isna(raw):
#         return None, None

#     raw = str(raw).replace("\n", " ").strip()
#     raw = re.sub(r"\s+", " ", raw)

#     if raw == "":
#         return None, None

#     num_match = re.search(r"\d+", raw)
#     sdg_number = num_match.group(0) if num_match else None
#     sdg_name = raw.replace(sdg_number or "", "").strip().title()

#     return sdg_number, sdg_name


# # =========================================================
# # CORE PARSER
# # =========================================================

# def reconstruct_rows(md_text: str):
#     """
#     Merge multiline markdown rows into logical table rows.
#     """
#     lines = [l.rstrip() for l in md_text.splitlines() if l.strip()]

#     logical_rows = []
#     buffer = ""

#     for line in lines:
#         if is_table_row_start(line):
#             if buffer:
#                 logical_rows.append(buffer)
#             buffer = line
#         else:
#             buffer += " " + line.strip()

#     if buffer:
#         logical_rows.append(buffer)

#     # Remove markdown header separators
#     logical_rows = [
#         row for row in logical_rows
#         if not re.match(r"^\|\s*-+", row)
#     ]

#     return logical_rows


# def parse_markdown_table(md_text: str) -> pd.DataFrame:
#     rows = reconstruct_rows(md_text)

#     parsed = []
#     header = None
#     expected_cols = None

#     for idx, row in enumerate(rows):
#         parts = [p.strip() for p in row.strip("|").split("|")]

#         # ----------------------------
#         # HEADER
#         # ----------------------------
#         if idx == 0:
#             header = parts
#             expected_cols = len(header)
#             parsed.append(parts)
#             continue

#         # ----------------------------
#         # FIX COLUMN MISMATCH
#         # ----------------------------

#         if len(parts) > expected_cols:
#             # Merge everything between [SDG, Target] and [Unit, Sources]
#             head = parts[:2]
#             tail = parts[-2:]
#             middle = parts[2:-2]

#             merged_disclosure = " | ".join(middle)
#             parts = head + [merged_disclosure] + tail

#         elif len(parts) < expected_cols:
#             # Pad missing columns
#             parts = parts + [""] * (expected_cols - len(parts))

#         parsed.append(parts)

#     df = pd.DataFrame(parsed[1:], columns=header)

#     # ----------------------------
#     # Clean cells
#     # ----------------------------

#     for col in df.columns:
#         df[col] = df[col].apply(clean_cell)

#     # ----------------------------
#     # Forward-fill SDG + normalize
#     # ----------------------------

#     if "SDG" in df.columns:
#         df["SDG"] = df["SDG"].replace("", pd.NA).ffill()

#         normalized = df["SDG"].apply(normalize_sdg)
#         df["SDG_Number"] = normalized.apply(lambda x: x[0])
#         df["SDG_Name"] = normalized.apply(lambda x: x[1])

#     # ----------------------------
#     # Column ordering
#     # ----------------------------

#     preferred = [
#         "SDG_Number",
#         "SDG_Name",
#         "Target",
#         "Available Business Disclosures",
#         "Unit",
#         "Sources",
#     ]

#     ordered = [c for c in preferred if c in df.columns]
#     remaining = [c for c in df.columns if c not in ordered]
#     df = df[ordered + remaining]

#     return df


# # =========================================================
# # UI
# # =========================================================

# if st.button("🚀 Parse Table"):
#     try:
#         df = parse_markdown_table(markdown_text)

#         st.success("✅ Table parsed successfully")

#         st.subheader("📊 Parsed Output")
#         st.dataframe(df, use_container_width=True)

#         # ----------------------------
#         # CSV Export
#         # ----------------------------

#         csv_buffer = StringIO()
#         df.to_csv(csv_buffer, index=False)

#         st.download_button(
#             "⬇️ Download CSV",
#             csv_buffer.getvalue(),
#             file_name="sdg_parsed.csv",
#             mime="text/csv"
#         )

#         with st.expander("🔍 Dataset Info"):
#             st.write("Rows:", len(df))
#             st.write("Columns:", df.columns.tolist())

#     except Exception as e:
#         st.error(f"❌ Parsing failed: {e}")


# import streamlit as st
# import pandas as pd
# import re
# from io import StringIO

# # =========================================================
# # PAGE CONFIG
# # =========================================================

# st.set_page_config(
#     page_title="🧾 PDF Markdown → CSV Parser",
#     layout="wide"
# )

# st.title("🧾 PDF Table Markdown Parser")
# st.caption("Robust parser for complex multi-line PDF extracted markdown tables")

# # =========================================================
# # INPUT
# # =========================================================

# markdown_text = st.text_area(
#     "📋 Paste Markdown Table Here",
#     height=420
# )

# # =========================================================
# # UTILITIES
# # =========================================================

# def is_table_row_start(line: str) -> bool:
#     """
#     A real table row starts with | and contains multiple pipe separators.
#     """
#     return line.strip().startswith("|") and line.count("|") >= 4


# def clean_cell(text: str) -> str:
#     """
#     Preserve bullets and normalize spacing.
#     """
#     if not text:
#         return ""

#     text = text.replace("\r\n", "\n").replace("\r", "\n")
#     text = re.sub(r"\n{3,}", "\n\n", text)

#     lines = [line.strip() for line in text.split("\n")]
#     return "\n".join(lines).strip()


# def normalize_sdg(raw: str):
#     """
#     Normalize SDG cell:
#         3
#         GOOD HEALTH
#         AND WELL-BEING
#     →
#         SDG_Number = 3
#         SDG_Name = Good Health And Well-Being
#     """
#     if not raw or raw.strip() == "":
#         return None, None

#     raw = raw.replace("\n", " ").strip()
#     raw = re.sub(r"\s+", " ", raw)

#     num_match = re.search(r"\d+", raw)
#     sdg_number = num_match.group(0) if num_match else None
#     sdg_name = raw.replace(sdg_number or "", "").strip().title()

#     return sdg_number, sdg_name


# # =========================================================
# # CORE PARSER
# # =========================================================

# def reconstruct_rows(md_text: str):
#     """
#     Merge multiline markdown rows into logical table rows.
#     """
#     lines = [l.rstrip() for l in md_text.splitlines() if l.strip()]

#     logical_rows = []
#     buffer = ""

#     for line in lines:
#         if is_table_row_start(line):
#             if buffer:
#                 logical_rows.append(buffer)
#             buffer = line
#         else:
#             buffer += " " + line.strip()

#     if buffer:
#         logical_rows.append(buffer)

#     # Remove markdown header separators
#     logical_rows = [
#         row for row in logical_rows
#         if not re.match(r"^\|\s*-+", row)
#     ]

#     return logical_rows


# def parse_markdown_table(md_text: str) -> pd.DataFrame:
#     rows = reconstruct_rows(md_text)

#     parsed = []
#     header = None
#     expected_cols = None

#     for idx, row in enumerate(rows):
#         parts = [p.strip() for p in row.strip("|").split("|")]

#         # ----------------------------
#         # HEADER
#         # ----------------------------
#         if idx == 0:
#             header = parts
#             expected_cols = len(header)
#             parsed.append(parts)
#             continue

#         # ----------------------------
#         # FIX COLUMN MISMATCH
#         # ----------------------------

#         if len(parts) > expected_cols:
#             """
#             Merge everything between:
#                 [SDG, Target] and [Unit, Sources]
#             """
#             head = parts[:2]
#             tail = parts[-2:]
#             middle = parts[2:-2]

#             merged_disclosure = " | ".join(middle)
#             parts = head + [merged_disclosure] + tail

#         elif len(parts) < expected_cols:
#             # Pad missing columns
#             parts = parts + [""] * (expected_cols - len(parts))

#         parsed.append(parts)

#     df = pd.DataFrame(parsed[1:], columns=header)

#     # ----------------------------
#     # Clean cells
#     # ----------------------------

#     for col in df.columns:
#         df[col] = df[col].astype(str).apply(clean_cell)

#     # ----------------------------
#     # Forward-fill SDG + normalize
#     # ----------------------------

#     if "SDG" in df.columns:
#         df["SDG"] = df["SDG"].replace("", pd.NA).ffill()

#         normalized = df["SDG"].apply(normalize_sdg)
#         df["SDG_Number"] = normalized.apply(lambda x: x[0])
#         df["SDG_Name"] = normalized.apply(lambda x: x[1])

#     # ----------------------------
#     # Column ordering
#     # ----------------------------

#     preferred = [
#         "SDG_Number",
#         "SDG_Name",
#         "Target",
#         "Available Business Disclosures",
#         "Unit",
#         "Sources",
#     ]

#     ordered = [c for c in preferred if c in df.columns]
#     remaining = [c for c in df.columns if c not in ordered]
#     df = df[ordered + remaining]

#     return df


# # =========================================================
# # UI
# # =========================================================

# if st.button("🚀 Parse Table"):
#     try:
#         df = parse_markdown_table(markdown_text)

#         st.success("✅ Table parsed successfully")

#         st.subheader("📊 Parsed Output")
#         st.dataframe(df, use_container_width=True)

#         # ----------------------------
#         # CSV Export
#         # ----------------------------

#         csv_buffer = StringIO()
#         df.to_csv(csv_buffer, index=False)

#         st.download_button(
#             "⬇️ Download CSV",
#             csv_buffer.getvalue(),
#             file_name="sdg_parsed.csv",
#             mime="text/csv"
#         )

#         with st.expander("🔍 Dataset Info"):
#             st.write("Rows:", len(df))
#             st.write("Columns:", df.columns.tolist())

#     except Exception as e:
#         st.error(f"❌ Parsing failed: {e}")

# import streamlit as st
# import pandas as pd
# import re
# from io import StringIO

# # =========================================================
# # PAGE CONFIG
# # =========================================================

# st.set_page_config(
#     page_title="🧾 PDF Markdown → CSV Parser",
#     layout="wide"
# )

# st.title("🧾 PDF Table Markdown Parser")
# st.caption("Robust parser for multi-line PDF-extracted markdown tables")

# # =========================================================
# # INPUT
# # =========================================================

# markdown_text = st.text_area(
#     "📋 Paste Markdown Table Here",
#     height=420
# )

# # =========================================================
# # LOW-LEVEL UTILITIES
# # =========================================================

# def is_table_row_start(line: str) -> bool:
#     """
#     Detect a real table row:
#     Must start with | and contain multiple column pipes.
#     """
#     return line.strip().startswith("|") and line.count("|") >= 4


# def clean_cell(text: str) -> str:
#     """
#     Preserve bullet formatting and normalize whitespace.
#     """
#     if not text:
#         return ""

#     text = text.replace("\r\n", "\n").replace("\r", "\n")

#     # Normalize excessive blank lines
#     text = re.sub(r"\n{3,}", "\n\n", text)

#     # Trim each line
#     lines = [line.strip() for line in text.split("\n")]
#     return "\n".join(lines).strip()


# def normalize_sdg(raw: str):
#     """
#     Convert:
#       3
#       GOOD HEALTH
#       AND WELL-GOING
#     →
#       SDG_Number = 3
#       SDG_Name = Good Health And Well-Going
#     """
#     if not raw or raw.strip() == "":
#         return None, None

#     raw = raw.replace("\n", " ").strip()
#     raw = re.sub(r"\s+", " ", raw)

#     num_match = re.search(r"\d+", raw)
#     sdg_number = num_match.group(0) if num_match else None

#     name = raw.replace(sdg_number or "", "").strip().title()

#     return sdg_number, name


# # =========================================================
# # CORE PARSER
# # =========================================================

# def reconstruct_rows(md_text: str):
#     """
#     Merge multiline markdown rows into logical table rows.
#     """
#     lines = [l.rstrip() for l in md_text.splitlines() if l.strip()]

#     logical_rows = []
#     buffer = ""

#     for line in lines:
#         if is_table_row_start(line):
#             if buffer:
#                 logical_rows.append(buffer)
#             buffer = line
#         else:
#             # continuation of previous row
#             buffer += " " + line.strip()

#     if buffer:
#         logical_rows.append(buffer)

#     # Remove header separator row
#     logical_rows = [
#         row for row in logical_rows
#         if not re.match(r"^\|\s*-+", row)
#     ]

#     return logical_rows


# def parse_markdown_table(md_text: str) -> pd.DataFrame:
#     rows = reconstruct_rows(md_text)

#     parsed = []
#     for row in rows:
#         parts = [p.strip() for p in row.strip("|").split("|")]
#         parsed.append(parts)

#     header = parsed[0]
#     data = parsed[1:]

#     df = pd.DataFrame(data, columns=header)

#     # --------------------------------
#     # Clean cells
#     # --------------------------------
#     for col in df.columns:
#         df[col] = df[col].astype(str).apply(clean_cell)

#     # --------------------------------
#     # Forward-fill SDG
#     # --------------------------------
#     if "SDG" in df.columns:
#         df["SDG"] = df["SDG"].replace("", pd.NA).ffill()

#         normalized = df["SDG"].apply(normalize_sdg)
#         df["SDG_Number"] = normalized.apply(lambda x: x[0])
#         df["SDG_Name"] = normalized.apply(lambda x: x[1])

#     # --------------------------------
#     # Reorder columns
#     # --------------------------------
#     preferred = [
#         "SDG_Number",
#         "SDG_Name",
#         "Target",
#         "Available Business Disclosures",
#         "Unit",
#         "Sources",
#     ]

#     ordered = [c for c in preferred if c in df.columns]
#     remaining = [c for c in df.columns if c not in ordered]
#     df = df[ordered + remaining]

#     return df


# # =========================================================
# # UI
# # =========================================================

# if st.button("🚀 Parse Table"):
#     try:
#         df = parse_markdown_table(markdown_text)

#         st.success("✅ Table parsed successfully")

#         st.subheader("📊 Parsed Output")
#         st.dataframe(df, use_container_width=True)

#         # Export CSV
#         csv_buffer = StringIO()
#         df.to_csv(csv_buffer, index=False)

#         st.download_button(
#             "⬇️ Download CSV",
#             csv_buffer.getvalue(),
#             file_name="sdg_parsed.csv",
#             mime="text/csv"
#         )

#         with st.expander("🔍 Debug Info"):
#             st.write("Rows:", len(df))
#             st.write("Columns:", df.columns.tolist())

#     except Exception as e:
#         st.error(f"❌ Parsing failed: {e}")


# import streamlit as st
# import pandas as pd
# import re
# from io import StringIO

# # =========================================================
# # PAGE CONFIG
# # =========================================================

# st.set_page_config(
#     page_title="🧾 Markdown Table → CSV Parser",
#     layout="wide"
# )

# st.title("🧾 Markdown Table → CSV Parser")
# st.caption("Paste markdown tables and convert them into clean CSV files")

# # =========================================================
# # INPUT
# # =========================================================

# default_text = """|  SDG | Target | Available Business Disclosures | Unit | Sources  |
# | --- | --- | --- | --- | --- |
# |  1
# NO
# POVERTY | 1.1 | The reporting organization shall report the following information:
# a. All tax jurisdictions where the entities included in the organization's audited consolidated financial statements, or in the financial information filed on public record, are resident for tax purposes.
# b. For each tax jurisdiction reported in Disclosure 207-4-a:
# i. Names of the resident entities;
# ii. Primary activities of the organization;
# iii. Number of employees, and the basis of calculation of this number;
# iv. Revenues from third-party sales;
# v. Revenues from intra-group transactions with other tax jurisdictions;
# vi. Profit/loss before tax;
# vii. Tangible assets other than cash and cash equivalents;
# viii. Corporate income tax paid on a cash basis;
# ix. Corporate income tax accrued on profit/loss;
# x. Reasons for the difference between corporate income tax accrued on profit/loss and the tax due if the statutory tax rate is applied to profit/loss before tax.
# c. The time period covered by the information reported in Disclosure 207-4 | N/A | GRI Standards 207-4  |
# |   |  1.2 | When a significant proportion of employees are compensated based on wages subject to minimum wage rules, report the relevant ratio of the entry level wage by gender at significant locations of operation to the minimum wage. | Ratio of the entry level wage by gender | GRI Standard 202-1  |
# |  1.2 | When a significant proportion of other workers (excluding employees) performing the organization's activities are compensated based on wages subject to minimum wage rules, describe the actions taken to determine whether these workers are paid above the minimum wage. | N/A | GRI Standard 202-1 |   |
# |  1.2 | Whether a local minimum wage is absent or variable at significant locations of operation, by gender. In circumstances in which different minimums can be used as a reference, report which minimum wage is being used. | $ currency | GRI Standard 202-1 |   |
# |  1.2 | Examples of significant identified indirect economic impacts of the organization, including positive and negative impacts. | N/A | GRI Standard 203-2 |   |
# |  1.2 | Significance of the indirect economic impacts in the context of external benchmarks and stakeholder priorities, such as national and international standards, protocols, and policy agendas. | N/A | GRI Standard 203-2 |   |"""

# markdown_text = st.text_area(
#     "📋 Paste Markdown Table Here",
#     value=default_text,
#     height=350
# )

# # =========================================================
# # PARSER
# # =========================================================

# def clean_cell(text: str) -> str:
#     """Normalize multiline cells and spacing"""
#     if not text:
#         return ""
#     text = re.sub(r"\s+", " ", text)
#     return text.strip()


# def parse_markdown_table(md_text: str) -> pd.DataFrame:
#     lines = [
#         line.strip()
#         for line in md_text.splitlines()
#         if line.strip().startswith("|")
#     ]

#     # Remove header separator row
#     lines = [line for line in lines if not re.match(r"^\|\s*-+", line)]

#     rows = []
#     for line in lines:
#         parts = [p.strip() for p in line.strip("|").split("|")]
#         rows.append(parts)

#     header = rows[0]
#     data_rows = rows[1:]

#     df = pd.DataFrame(data_rows, columns=header)

#     # Clean every cell
#     for col in df.columns:
#         df[col] = df[col].astype(str).apply(clean_cell)

#     # Forward-fill SDG if empty
#     if "SDG" in df.columns:
#         df["SDG"] = df["SDG"].replace("", pd.NA).ffill()

#     return df


# # =========================================================
# # ACTIONS
# # =========================================================

# if st.button("🚀 Parse Markdown"):
#     try:
#         df = parse_markdown_table(markdown_text)

#         st.success("✅ Table parsed successfully")

#         st.subheader("📊 Parsed Table Preview")
#         st.dataframe(df, use_container_width=True)

#         # CSV Export
#         csv_buffer = StringIO()
#         df.to_csv(csv_buffer, index=False)

#         st.download_button(
#             "⬇️ Download CSV",
#             csv_buffer.getvalue(),
#             file_name="sdg_disclosures.csv",
#             mime="text/csv"
#         )

#         # Optional Stats
#         with st.expander("📈 Dataset Summary"):
#             st.write("Rows:", len(df))
#             st.write("Columns:", list(df.columns))

#     except Exception as e:
#         st.error(f"❌ Parsing failed: {e}")
