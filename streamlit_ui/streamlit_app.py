"""Manual test / demo UI for the NP Planning API -- a thin HTTP client, not the real Customer
Mode product UI (there is no real product UI yet; this exists to exercise and demo the backend).

Configure the backend URL via the NP_PLANNING_API_BASE environment variable or an
`api_base` entry in Streamlit secrets -- defaults to a local dev server. If you deploy this to
Streamlit Community Cloud, it can only reach a backend that is itself publicly reachable; it
cannot talk to a `localhost` FastAPI process running on someone's own machine. Point it at a
real deployed API, or run both locally together for now.

Optionally pre-fill the login form via `default_email` / `default_password` in Streamlit
secrets (`.streamlit/secrets.toml` locally -- gitignored, never commit real credentials; the
app's own Secrets panel on Streamlit Cloud) so testers don't retype them every run.
"""

import json
import os

import requests
import streamlit as st

DEFAULT_API_BASE = "http://127.0.0.1:8000"

# Field/button labels only -- API field names, JSON payloads, and endpoint paths stay in
# English regardless of UI language, since they must match the backend exactly.
TEXT = {
    "app_title": {"en": "NP Planning -- manual test UI", "th": "NP Planning -- หน้าทดสอบใช้งาน"},
    "app_caption": {
        "en": "Talking to {api_base}. This is a thin HTTP test client for the backend, not the real Customer Mode product UI.",
        "th": "เชื่อมต่อกับ {api_base} หน้านี้เป็นแค่ตัวทดสอบยิง API เข้า backend ไม่ใช่หน้าตาโปรแกรมจริงของลูกค้า",
    },
    "login_header": {"en": "Login", "th": "เข้าสู่ระบบ"},
    "logged_in": {"en": "Logged in", "th": "เข้าสู่ระบบแล้ว"},
    "log_out": {"en": "Log out", "th": "ออกจากระบบ"},
    "email": {"en": "Email", "th": "อีเมล"},
    "password": {"en": "Password", "th": "รหัสผ่าน"},
    "log_in": {"en": "Log in", "th": "เข้าสู่ระบบ"},
    "default_site_caption": {
        "en": "Site ID used as the default across tabs (paste a real one)",
        "th": "Site ID ที่ใช้เป็นค่าเริ่มต้นในทุกแท็บ (วาง Site ID จริงตรงนี้)",
    },
    "default_site_id": {"en": "Default Site ID", "th": "Site ID เริ่มต้น"},
    "login_prompt": {
        "en": "Log in from the sidebar to test the protected endpoints.",
        "th": "เข้าสู่ระบบจากแถบด้านข้างก่อน เพื่อทดสอบ endpoint ที่ต้องยืนยันตัวตน",
    },
    "could_not_reach": {
        "en": "Could not reach {api_base} -- is the backend running and reachable from here?",
        "th": "เชื่อมต่อ {api_base} ไม่ได้ -- backend รันอยู่ไหม และเข้าถึงได้จากตรงนี้หรือเปล่า?",
    },
    "invalid_json": {"en": "Invalid JSON: {error}", "th": "รูปแบบ JSON ไม่ถูกต้อง: {error}"},
    # Tab names
    "tab_sites": {"en": "Sites", "th": "สถานที่ (Sites)"},
    "tab_canopy": {"en": "Canopy configurator", "th": "ตั้งค่ากันสาด"},
    "tab_confirm": {"en": "Confirm quote", "th": "ยืนยันใบเสนอราคา"},
    "tab_business": {"en": "Business health", "th": "ภาพรวมธุรกิจ"},
    "tab_opportunities": {"en": "Opportunities", "th": "โอกาสการขาย"},
    "tab_specs": {"en": "Critical specs", "th": "สเปกสำคัญ"},
    "tab_quality": {"en": "Site quality", "th": "คุณภาพลูกค้า/สถานที่"},
    "tab_knowledge": {"en": "Site knowledge", "th": "ข้อมูลสถานที่"},
    "tab_website": {"en": "Website studio", "th": "จัดการเว็บไซต์"},
    "tab_products": {"en": "Products", "th": "สินค้า"},
    "tab_recipes": {"en": "Recipes", "th": "สูตรคำนวณ"},
    "tab_suppliers": {"en": "Suppliers", "th": "ซัพพลายเออร์"},
    "tab_raw": {"en": "Raw API call", "th": "ยิง API เอง"},
    # Sites tab
    "sites_caption": {
        "en": "Most other tabs need a Site ID -- create one here first. customer_name is get-or-create.",
        "th": "แท็บอื่นๆ ส่วนใหญ่ต้องใช้ Site ID -- สร้างที่นี่ก่อน customer_name ถ้ามีอยู่แล้วจะใช้ตัวเดิม ถ้ายังไม่มีจะสร้างใหม่ให้",
    },
    "customer_name": {"en": "Customer name", "th": "ชื่อลูกค้า"},
    "site_type": {"en": "Site type", "th": "ประเภทสถานที่"},
    "site_name": {"en": "Site name", "th": "ชื่อสถานที่"},
    "address_optional": {"en": "Address (optional)", "th": "ที่อยู่ (ใส่หรือไม่ใส่ก็ได้)"},
    "create_site": {"en": "Create site", "th": "สร้างสถานที่"},
    # Canopy tab
    "site_id": {"en": "Site ID", "th": "Site ID"},
    "width_m": {"en": "Width (m)", "th": "ความกว้าง (ม.)"},
    "length_m": {"en": "Length (m)", "th": "ความยาว (ม.)"},
    "roof_cover": {"en": "Roof cover", "th": "วัสดุมุงหลังคา"},
    "unit_cost_manual": {"en": "Unit cost per m2 (manual)", "th": "ต้นทุนต่อ ตร.ม. (กรอกเอง)"},
    "configure_canopy": {"en": "Configure canopy", "th": "ตั้งค่ากันสาด"},
    # Confirm quote tab
    "confirm_caption": {
        "en": "Every canopy quote's gate is OVERRIDE_REQUIRED (placeholder quantity basis, C3) -- an override_reason is required.",
        "th": "ใบเสนอราคากันสาดทุกใบจะติด gate OVERRIDE_REQUIRED เสมอ (เพราะฐานคำนวณปริมาณยังเป็น placeholder ตาม C3) -- ต้องกรอกเหตุผล override ทุกครั้ง",
    },
    "project_id": {"en": "Project ID", "th": "Project ID"},
    "quote_id": {"en": "Quote ID", "th": "Quote ID"},
    "confirmed_by": {"en": "Confirmed by", "th": "ผู้ยืนยัน"},
    "override_reason": {"en": "Override reason", "th": "เหตุผลที่ override"},
    "confirm_quote": {"en": "Confirm quote", "th": "ยืนยันใบเสนอราคา"},
    "what_if_caption": {"en": "What-if (POST /quotes/{id}/what-if)", "th": "จำลองสถานการณ์ (What-if)"},
    "cost_change_pct": {"en": "Cost change %", "th": "% ต้นทุนที่เปลี่ยน"},
    "simulate_cost_change": {"en": "Simulate cost change", "th": "จำลองต้นทุนเปลี่ยน"},
    "discount_pct": {"en": "Discount %", "th": "% ส่วนลด"},
    "simulate_discount": {"en": "Simulate discount", "th": "จำลองส่วนลด"},
    "recommendations_caption": {
        "en": "Recommendations (GET /quotes/{id}/recommendations)",
        "th": "คำแนะนำ (Recommendations)",
    },
    "fetch_recommendations": {"en": "Fetch recommendations", "th": "ดึงคำแนะนำ"},
    # Business health tab
    "as_of": {"en": "as_of (ISO datetime, optional)", "th": "ดูข้อมูล ณ วันที่ (ใส่หรือไม่ใส่ก็ได้)"},
    "refresh_dashboard": {"en": "Refresh dashboard", "th": "รีเฟรชแดชบอร์ด"},
    # Opportunities tab
    "source": {"en": "Source", "th": "ที่มา"},
    "description": {"en": "Description", "th": "รายละเอียด"},
    "create_opportunity": {"en": "Create opportunity", "th": "สร้างโอกาสการขาย"},
    "convert_caption": {"en": "POST /opportunities/{id}/convert", "th": "แปลงเป็นโปรเจกต์"},
    "opportunity_id": {"en": "Opportunity ID", "th": "Opportunity ID"},
    "project_data_json": {"en": "Project data (JSON)", "th": "ข้อมูลโปรเจกต์ (JSON)"},
    "convert_to_project": {"en": "Convert to project", "th": "แปลงเป็นโปรเจกต์"},
    # Critical specs tab
    "spec_type": {"en": "Spec type", "th": "ประเภทสเปก"},
    "create_critical_spec": {"en": "Create critical spec", "th": "สร้างสเปกสำคัญ"},
    "transition_caption": {"en": "POST /critical-specs/{id}/transition", "th": "เปลี่ยนสถานะสเปก"},
    "critical_spec_id": {"en": "Critical Spec ID", "th": "Critical Spec ID"},
    "transition_to": {"en": "Transition to", "th": "เปลี่ยนสถานะเป็น"},
    "confirmed_by_optional": {
        "en": "Confirmed by (only used for CONFIRMED)",
        "th": "ผู้ยืนยัน (ใช้เฉพาะตอนเปลี่ยนเป็น CONFIRMED)",
    },
    "transition_spec": {"en": "Transition spec", "th": "เปลี่ยนสถานะสเปก"},
    # Site quality tab
    "flag_type": {"en": "Flag type", "th": "ประเภทปัญหา"},
    "flag_description": {"en": "Description", "th": "รายละเอียด"},
    "flagged_by": {"en": "Flagged by", "th": "ผู้แจ้ง"},
    "flag_site": {"en": "Flag site", "th": "ปักธงปัญหา"},
    "check_site_health": {"en": "Check site health", "th": "เช็คสถานะลูกค้า/สถานที่"},
    "flag_id_to_resolve": {"en": "Flag ID to resolve", "th": "Flag ID ที่จะปิดปัญหา"},
    "resolve_flag": {"en": "Resolve flag", "th": "ปิดปัญหา"},
    # Site knowledge tab
    "fetch_observations": {"en": "Fetch observations", "th": "ดึงข้อมูลที่บันทึกไว้"},
    "survey_checklist_caption": {
        "en": "GET /sites/{id}/survey-checklist", "th": "รายการที่ต้องสำรวจหน้างาน",
    },
    "knowledge_types": {"en": "Knowledge types (comma-separated)", "th": "ประเภทข้อมูล (คั่นด้วยจุลภาค)"},
    "fetch_survey_checklist": {"en": "Fetch survey checklist", "th": "ดึงรายการสำรวจ"},
    # Website studio tab
    "branch_name": {"en": "Branch name", "th": "ชื่อ Branch"},
    "create_branch": {"en": "Create branch", "th": "สร้าง Branch"},
    "create_page_caption": {"en": "POST /website/pages", "th": "สร้างหน้าเว็บ"},
    "branch_id": {"en": "Branch ID", "th": "Branch ID"},
    "slug": {"en": "Slug", "th": "Slug"},
    "widget_type": {"en": "Widget type", "th": "ประเภท Widget"},
    "create_page": {"en": "Create page", "th": "สร้างหน้าเว็บ"},
    "update_page_caption": {"en": "PUT /website/pages/{id}", "th": "แก้ไขหน้าเว็บ"},
    "page_id": {"en": "Page ID", "th": "Page ID"},
    "new_widget_type": {"en": "New widget type", "th": "ประเภท Widget ใหม่"},
    "update_page": {"en": "Update page", "th": "อัปเดตหน้าเว็บ"},
    "restore_page_caption": {"en": "POST /website/pages/{id}/restore", "th": "ย้อนกลับหน้าเว็บ"},
    "restore_revision_number": {
        "en": "Restore to revision number", "th": "ย้อนกลับไปเวอร์ชันที่",
    },
    "restore_revision": {"en": "Restore revision", "th": "ย้อนกลับเวอร์ชัน"},
    # Products tab
    "list_products": {"en": "List products", "th": "แสดงรายการสินค้า"},
    # Recipes tab
    "recipes_caption": {
        "en": "Needs a real Product ID -- fetch one from the Products tab, or create one via the canopy configurator (which auto-creates the CANOPY product).",
        "th": "ต้องใช้ Product ID จริง -- ไปดึงจากแท็บ Products หรือสร้างผ่านแท็บตั้งค่ากันสาด (ระบบจะสร้างสินค้า CANOPY ให้อัตโนมัติ)",
    },
    "product_id": {"en": "Product ID", "th": "Product ID"},
    "recipe_name": {"en": "Recipe name", "th": "ชื่อสูตร"},
    "formula_json": {"en": "Formula (JSON)", "th": "สูตรคำนวณ (JSON)"},
    "create_recipe": {"en": "Create recipe", "th": "สร้างสูตร"},
    "recipe_id": {"en": "Recipe ID", "th": "Recipe ID"},
    "new_formula_json": {"en": "New formula (JSON)", "th": "สูตรคำนวณใหม่ (JSON)"},
    "update_recipe": {"en": "Update recipe", "th": "อัปเดตสูตร"},
    "restore_version_number": {"en": "Restore to version number", "th": "ย้อนกลับไปเวอร์ชันที่"},
    "restore_recipe_version": {"en": "Restore recipe version", "th": "ย้อนกลับเวอร์ชันสูตร"},
    # Suppliers tab
    "supplier_name": {"en": "Supplier name", "th": "ชื่อซัพพลายเออร์"},
    "create_supplier": {"en": "Create supplier", "th": "สร้างซัพพลายเออร์"},
    "supplier_quote_caption": {"en": "POST /suppliers/quotes", "th": "บันทึกใบเสนอราคาซัพพลายเออร์"},
    "supplier_id": {"en": "Supplier ID", "th": "Supplier ID"},
    "material_description": {"en": "Material description", "th": "รายละเอียดวัสดุ"},
    "quoted_price": {"en": "Quoted price", "th": "ราคาที่เสนอ"},
    "validity_days": {"en": "Validity (days)", "th": "ยืนราคา (วัน)"},
    "lock_days": {"en": "Lock (days)", "th": "ล็อกราคา (วัน)"},
    "lead_time_days": {"en": "Lead time (days)", "th": "ระยะเวลาส่งมอบ (วัน)"},
    "quote_date": {"en": "Quote date", "th": "วันที่เสนอราคา"},
    "create_supplier_quote": {"en": "Create supplier quote", "th": "บันทึกใบเสนอราคา"},
    "actual_procurement_caption": {
        "en": "POST /suppliers/quotes/{id}/actual-procurement", "th": "บันทึกราคาจัดซื้อจริง",
    },
    "supplier_quote_id": {"en": "Supplier Quote ID", "th": "Supplier Quote ID"},
    "actual_price": {"en": "Actual price", "th": "ราคาจริง"},
    "actual_lead_time": {"en": "Actual lead time (days)", "th": "ระยะเวลาส่งมอบจริง (วัน)"},
    "record_actual_procurement": {"en": "Record actual procurement", "th": "บันทึกการจัดซื้อจริง"},
    # Raw API call tab
    "any_endpoint": {"en": "Any endpoint", "th": "ยิง endpoint ไหนก็ได้"},
    "method": {"en": "Method", "th": "Method"},
    "path": {"en": "Path", "th": "Path"},
    "json_body": {"en": "JSON body (for POST/PUT)", "th": "JSON body (สำหรับ POST/PUT)"},
    "send": {"en": "Send", "th": "ส่ง"},
}


def _resolve_api_base() -> str:
    if "api_base" in st.secrets:
        return st.secrets["api_base"]
    return os.environ.get("NP_PLANNING_API_BASE", DEFAULT_API_BASE)


API_BASE = _resolve_api_base()

_STATE_KEYS = [
    "token", "last_project_id", "last_quote_id", "last_opportunity_id", "last_spec_id",
    "last_site_id", "last_flag_id", "last_branch_id", "last_page_id", "last_recipe_id",
    "last_product_id", "last_supplier_id", "last_supplier_quote_id", "lang",
]
for key in _STATE_KEYS:
    if key not in st.session_state:
        st.session_state[key] = None
if st.session_state.lang is None:
    st.session_state.lang = "th"


def t(key: str, **fmt) -> str:
    text = TEXT[key][st.session_state.lang]
    return text.format(**fmt) if fmt else text


st.set_page_config(page_title="NP Planning -- manual test UI", layout="wide")

with st.sidebar:
    lang_choice = st.radio(
        "Language / ภาษา", ["ไทย", "English"],
        index=0 if st.session_state.lang == "th" else 1, horizontal=True, key="lang_choice",
    )
    st.session_state.lang = "th" if lang_choice == "ไทย" else "en"
    st.divider()

st.title(t("app_title"))
st.caption(t("app_caption", api_base=API_BASE))


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}


def call(method: str, path: str, **kwargs):
    try:
        response = requests.request(method, f"{API_BASE}{path}", headers=auth_headers(), timeout=15, **kwargs)
    except requests.exceptions.ConnectionError:
        st.error(t("could_not_reach", api_base=API_BASE))
        return None
    if response.status_code < 300:
        st.success(f"{response.status_code}")
        try:
            body = response.json()
        except ValueError:
            body = None
        if body is not None:
            st.json(body)
        return body
    st.error(f"{response.status_code}: {response.text}")
    return None


with st.sidebar:
    st.header(t("login_header"))
    if st.session_state.token:
        st.success(t("logged_in"))
        if st.button(t("log_out"), key="log_out_btn"):
            requests.post(f"{API_BASE}/auth/logout", headers=auth_headers())
            st.session_state.token = None
            st.rerun()
    else:
        email = st.text_input(t("email"), value=st.secrets.get("default_email", ""), key="login_email")
        password = st.text_input(
            t("password"), type="password", value=st.secrets.get("default_password", ""), key="login_password"
        )
        if st.button(t("log_in"), key="log_in_btn"):
            response = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
            if response.status_code == 200:
                st.session_state.token = response.json()["token"]
                st.rerun()
            else:
                st.error(f"{response.status_code}: {response.text}")
    st.divider()
    st.caption(t("default_site_caption"))
    st.session_state.last_site_id = st.text_input(
        t("default_site_id"), value=st.session_state.last_site_id or "", key="default_site_id_input"
    )

if not st.session_state.token:
    st.info(t("login_prompt"))
    st.stop()

(
    tab_sites, tab_canopy, tab_confirm, tab_business, tab_opportunities, tab_specs, tab_quality,
    tab_knowledge, tab_website, tab_products, tab_recipes, tab_suppliers, tab_raw,
) = st.tabs(
    [
        t("tab_sites"), t("tab_canopy"), t("tab_confirm"), t("tab_business"), t("tab_opportunities"),
        t("tab_specs"), t("tab_quality"), t("tab_knowledge"), t("tab_website"), t("tab_products"),
        t("tab_recipes"), t("tab_suppliers"), t("tab_raw"),
    ]
)

with tab_sites:
    st.subheader("POST /sites")
    st.caption(t("sites_caption"))
    customer_name = st.text_input(t("customer_name"), value="Test Customer", key="sites_customer_name")
    site_type = st.selectbox(t("site_type"), ["HOME", "OFFICE", "FACTORY"], key="sites_site_type")
    site_name = st.text_input(t("site_name"), value="Test Site", key="sites_site_name")
    site_address = st.text_input(t("address_optional"), value="", key="sites_address")
    if st.button(t("create_site"), key="sites_create_btn"):
        body = call(
            "POST", "/sites",
            json={
                "customer_name": customer_name, "site_type": site_type,
                "name": site_name, "address": site_address or None,
            },
        )
        if body:
            st.session_state.last_site_id = body["id"]

with tab_canopy:
    st.subheader("POST /canopy/configure")
    site_id = st.text_input(t("site_id"), value=st.session_state.last_site_id or "", key="canopy_site_id")
    col1, col2 = st.columns(2)
    width_m = col1.number_input(t("width_m"), value=6.0, min_value=0.1, key="canopy_width_m")
    length_m = col2.number_input(t("length_m"), value=4.0, min_value=0.1, key="canopy_length_m")
    roof_cover = st.selectbox(
        t("roof_cover"), ["Metal Sheet", "Polycarbonate", "Vinyl", "D-Lite", "Shinkolite"], key="canopy_roof_cover"
    )
    unit_cost_per_m2 = st.number_input(t("unit_cost_manual"), value=1500.0, min_value=0.0, key="canopy_unit_cost")

    if st.button(t("configure_canopy"), key="canopy_configure_btn"):
        body = call(
            "POST", "/canopy/configure",
            json={
                "site_id": site_id, "width_m": width_m, "length_m": length_m,
                "roof_cover": roof_cover, "unit_cost_per_m2": unit_cost_per_m2,
            },
        )
        if body:
            st.session_state.last_project_id = body["project_id"]
            st.session_state.last_quote_id = body["quote_id"]

with tab_confirm:
    st.subheader("POST /quotes/confirm")
    st.caption(t("confirm_caption"))
    project_id = st.text_input(t("project_id"), value=st.session_state.last_project_id or "", key="confirm_project_id")
    quote_id = st.text_input(t("quote_id"), value=st.session_state.last_quote_id or "", key="confirm_quote_id")
    confirmed_by = st.text_input(t("confirmed_by"), value="Test Admin", key="confirm_confirmed_by")
    override_reason = st.text_input(t("override_reason"), value="Manual test confirmation", key="confirm_override_reason")

    if st.button(t("confirm_quote"), key="confirm_quote_btn"):
        call(
            "POST", "/quotes/confirm",
            json={
                "project_id": project_id, "quote_id": quote_id,
                "confirmed_by": confirmed_by, "override_reason": override_reason or None,
            },
        )

    if quote_id:
        st.divider()
        st.caption(t("what_if_caption"))
        wcol1, wcol2 = st.columns(2)
        cost_change = wcol1.number_input(t("cost_change_pct"), value=8.0, key="confirm_cost_change")
        if wcol1.button(t("simulate_cost_change"), key="confirm_simulate_cost_btn"):
            call("POST", f"/quotes/{quote_id}/what-if", json={"cost_change_percent": cost_change})
        discount = wcol2.number_input(t("discount_pct"), value=5.0, key="confirm_discount")
        if wcol2.button(t("simulate_discount"), key="confirm_simulate_discount_btn"):
            call("POST", f"/quotes/{quote_id}/what-if", json={"discount_percent": discount})

        st.caption(t("recommendations_caption"))
        if st.button(t("fetch_recommendations"), key="confirm_fetch_recommendations_btn"):
            call("GET", f"/quotes/{quote_id}/recommendations")

with tab_business:
    st.subheader("GET /business/health")
    as_of = st.text_input(t("as_of"), value="", key="business_as_of")
    if st.button(t("refresh_dashboard"), key="business_refresh_btn"):
        params = {"as_of": as_of} if as_of else None
        call("GET", "/business/health", params=params)

with tab_opportunities:
    st.subheader("POST /opportunities")
    opp_site_id = st.text_input(t("site_id"), value=st.session_state.last_site_id or "", key="opp_site_id")
    source = st.selectbox(t("source"), ["website_inquiry", "referral", "repeat_customer"], key="opp_source")
    description = st.text_input(t("description"), value="Manual test opportunity", key="opp_description")
    if st.button(t("create_opportunity"), key="opp_create_btn"):
        body = call("POST", "/opportunities", json={"site_id": opp_site_id, "source": source, "description": description})
        if body:
            st.session_state.last_opportunity_id = body["id"]

    st.divider()
    st.caption(t("convert_caption"))
    opportunity_id = st.text_input(t("opportunity_id"), value=st.session_state.last_opportunity_id or "", key="opp_opportunity_id")
    project_data = st.text_area(t("project_data_json"), value='{"name": "Converted from opportunity"}', key="opp_project_data")
    if st.button(t("convert_to_project"), key="opp_convert_btn"):
        try:
            parsed = json.loads(project_data)
        except json.JSONDecodeError as e:
            st.error(t("invalid_json", error=e))
        else:
            body = call("POST", f"/opportunities/{opportunity_id}/convert", json={"project_data": parsed})
            if body:
                st.session_state.last_project_id = body["project_id"]

with tab_specs:
    st.subheader("POST /critical-specs")
    spec_project_id = st.text_input(t("project_id"), value=st.session_state.last_project_id or "", key="spec_project_id")
    spec_type = st.text_input(t("spec_type"), value="roof_material_model", key="specs_spec_type")
    spec_description = st.text_input(t("description"), value="TBD", key="specs_description")
    if st.button(t("create_critical_spec"), key="specs_create_btn"):
        body = call("POST", "/critical-specs", json={"project_id": spec_project_id, "spec_type": spec_type, "description": spec_description})
        if body:
            st.session_state.last_spec_id = body["id"]

    st.divider()
    st.caption(t("transition_caption"))
    spec_id = st.text_input(t("critical_spec_id"), value=st.session_state.last_spec_id or "", key="specs_spec_id")
    to_state = st.selectbox(t("transition_to"), ["PROPOSED", "CONFIRMED"], key="specs_to_state")
    spec_confirmed_by = st.text_input(t("confirmed_by_optional"), value="Estimator J.", key="specs_confirmed_by")
    if st.button(t("transition_spec"), key="specs_transition_btn"):
        call("POST", f"/critical-specs/{spec_id}/transition", json={"to_state": to_state, "confirmed_by": spec_confirmed_by})

with tab_quality:
    st.subheader("POST /sites/{id}/quality-flags")
    quality_site_id = st.text_input(t("site_id"), value=st.session_state.last_site_id or "", key="quality_site_id")
    flag_type = st.selectbox(
        t("flag_type"),
        ["BAD_PAYMENT", "REPEATED_SCOPE_ABUSE", "MARGIN_LEAKAGE", "HIGH_DISPUTE", "EXCESSIVE_ADMIN_BURDEN", "UNSAFE_PRACTICES", "POOR_CAPACITY_FIT"],
        key="quality_flag_type",
    )
    flag_description = st.text_input(t("flag_description"), value="Manual test flag", key="quality_flag_description")
    flagged_by = st.text_input(t("flagged_by"), value="PM K.", key="quality_flagged_by")
    if st.button(t("flag_site"), key="quality_flag_btn"):
        body = call(
            "POST", f"/sites/{quality_site_id}/quality-flags",
            json={"flag_type": flag_type, "description": flag_description, "flagged_by": flagged_by},
        )
        if body:
            st.session_state.last_flag_id = body["id"]

    st.divider()
    if st.button(t("check_site_health"), key="quality_check_btn"):
        call("GET", f"/sites/{quality_site_id}/quality")

    st.divider()
    flag_id = st.text_input(t("flag_id_to_resolve"), value=st.session_state.last_flag_id or "", key="quality_flag_id")
    if st.button(t("resolve_flag"), key="quality_resolve_btn"):
        call("POST", f"/quality-flags/{flag_id}/resolve")

with tab_knowledge:
    st.subheader("GET /sites/{id}/knowledge")
    knowledge_site_id = st.text_input(t("site_id"), value=st.session_state.last_site_id or "", key="knowledge_site_id")
    if st.button(t("fetch_observations"), key="knowledge_fetch_btn"):
        call("GET", f"/sites/{knowledge_site_id}/knowledge")

    st.divider()
    st.caption(t("survey_checklist_caption"))
    knowledge_types = st.text_input(t("knowledge_types"), value="pile_depth,soil_bearing", key="knowledge_types_input")
    if st.button(t("fetch_survey_checklist"), key="knowledge_checklist_btn"):
        call("GET", f"/sites/{knowledge_site_id}/survey-checklist", params={"knowledge_types": knowledge_types})

with tab_website:
    st.subheader("POST /website/branches")
    branch_name = st.text_input(t("branch_name"), value="MAIN", key="website_branch_name")
    if st.button(t("create_branch"), key="website_create_branch_btn"):
        body = call("POST", "/website/branches", json={"name": branch_name})
        if body:
            st.session_state.last_branch_id = body["id"]

    st.divider()
    st.caption(t("create_page_caption"))
    branch_id = st.text_input(t("branch_id"), value=st.session_state.last_branch_id or "", key="website_branch_id")
    slug = st.text_input(t("slug"), value="home", key="website_slug")
    widget_type = st.text_input(t("widget_type"), value="Hero", key="website_widget_type")
    if st.button(t("create_page"), key="website_create_page_btn"):
        body = call(
            "POST", "/website/pages",
            json={"branch_id": branch_id, "slug": slug, "widgets": [{"widget_type": widget_type, "order_index": 0}]},
        )
        if body:
            st.session_state.last_page_id = body["page_id"]

    st.divider()
    st.caption(t("update_page_caption"))
    page_id = st.text_input(t("page_id"), value=st.session_state.last_page_id or "", key="website_page_id")
    new_widget_type = st.text_input(t("new_widget_type"), value="ServiceCards", key="website_new_widget_type")
    if st.button(t("update_page"), key="website_update_page_btn"):
        call("PUT", f"/website/pages/{page_id}", json={"widgets": [{"widget_type": new_widget_type, "order_index": 0}]})

    st.divider()
    st.caption(t("restore_page_caption"))
    restore_to = st.number_input(t("restore_revision_number"), value=1, min_value=1, step=1, key="website_restore_to")
    if st.button(t("restore_revision"), key="website_restore_btn"):
        call("POST", f"/website/pages/{page_id}/restore", json={"target_revision_number": int(restore_to)})

with tab_products:
    st.subheader("GET /products")
    if st.button(t("list_products"), key="products_list_btn"):
        body = call("GET", "/products")
        if body:
            st.session_state.last_product_id = body[0]["id"] if body else None

with tab_recipes:
    st.subheader("POST /recipes")
    st.caption(t("recipes_caption"))
    product_id = st.text_input(t("product_id"), value=st.session_state.last_product_id or "", key="recipes_product_id")
    recipe_name = st.text_input(t("recipe_name"), value="Standard", key="recipes_recipe_name")
    formula_text = st.text_area(t("formula_json"), value='{"waste_factor": 0.05}', key="recipes_formula_text")
    if st.button(t("create_recipe"), key="recipes_create_btn"):
        try:
            formula = json.loads(formula_text)
        except json.JSONDecodeError as e:
            st.error(t("invalid_json", error=e))
        else:
            body = call("POST", "/recipes", json={"product_id": product_id, "name": recipe_name, "formula": formula})
            if body:
                st.session_state.last_recipe_id = body["recipe_id"]

    st.divider()
    recipe_id = st.text_input(t("recipe_id"), value=st.session_state.last_recipe_id or "", key="recipes_recipe_id")
    new_formula_text = st.text_area(t("new_formula_json"), value='{"waste_factor": 0.08}', key="recipes_new_formula_text")
    if st.button(t("update_recipe"), key="recipes_update_btn"):
        try:
            new_formula = json.loads(new_formula_text)
        except json.JSONDecodeError as e:
            st.error(t("invalid_json", error=e))
        else:
            call("PUT", f"/recipes/{recipe_id}", json={"formula": new_formula})

    st.divider()
    restore_version = st.number_input(t("restore_version_number"), value=1, min_value=1, step=1, key="recipes_restore_version")
    if st.button(t("restore_recipe_version"), key="recipes_restore_btn"):
        call("POST", f"/recipes/{recipe_id}/restore", json={"target_version_number": int(restore_version)})

with tab_suppliers:
    st.subheader("POST /suppliers")
    supplier_name = st.text_input(t("supplier_name"), value="Supplier A", key="suppliers_supplier_name")
    if st.button(t("create_supplier"), key="suppliers_create_btn"):
        body = call("POST", "/suppliers", json={"name": supplier_name})
        if body:
            st.session_state.last_supplier_id = body["id"]

    st.divider()
    st.caption(t("supplier_quote_caption"))
    supplier_id = st.text_input(t("supplier_id"), value=st.session_state.last_supplier_id or "", key="suppliers_supplier_id")
    material_description = st.text_input(t("material_description"), value="Metal Sheet Roofing, 0.35mm", key="suppliers_material_description")
    qcol1, qcol2, qcol3 = st.columns(3)
    quoted_price = qcol1.number_input(t("quoted_price"), value=98.0, key="suppliers_quoted_price")
    validity_days = qcol2.number_input(t("validity_days"), value=14, step=1, key="suppliers_validity_days")
    lock_days = qcol3.number_input(t("lock_days"), value=30, step=1, key="suppliers_lock_days")
    lead_time_days = st.number_input(t("lead_time_days"), value=21, step=1, key="suppliers_lead_time_days")
    quote_date = st.date_input(t("quote_date"), key="suppliers_quote_date")
    if st.button(t("create_supplier_quote"), key="suppliers_create_quote_btn"):
        body = call(
            "POST", "/suppliers/quotes",
            json={
                "supplier_id": supplier_id, "material_description": material_description,
                "quoted_price": quoted_price, "quote_date": str(quote_date),
                "validity_days": int(validity_days), "lock_days": int(lock_days),
                "lead_time_days": int(lead_time_days),
            },
        )
        if body:
            st.session_state.last_supplier_quote_id = body["id"]

    st.divider()
    st.caption(t("actual_procurement_caption"))
    supplier_quote_id = st.text_input(t("supplier_quote_id"), value=st.session_state.last_supplier_quote_id or "", key="suppliers_supplier_quote_id")
    actual_price = st.number_input(t("actual_price"), value=99.5, key="suppliers_actual_price")
    actual_lead_time = st.number_input(t("actual_lead_time"), value=25, step=1, key="suppliers_actual_lead_time")
    if st.button(t("record_actual_procurement"), key="suppliers_record_actual_btn"):
        call(
            "POST", f"/suppliers/quotes/{supplier_quote_id}/actual-procurement",
            json={"actual_price": actual_price, "actual_lead_time_days": int(actual_lead_time)},
        )

with tab_raw:
    st.subheader(t("any_endpoint"))
    method = st.selectbox(t("method"), ["GET", "POST", "PUT"], key="raw_method")
    path = st.text_input(t("path"), value="/business/health", key="raw_path")
    body_text = st.text_area(t("json_body"), value="{}", key="raw_body_text")
    if st.button(t("send"), key="raw_send_btn"):
        try:
            body = json.loads(body_text) if body_text.strip() else None
        except json.JSONDecodeError as e:
            st.error(t("invalid_json", error=e))
        else:
            call(method, path, json=body)
