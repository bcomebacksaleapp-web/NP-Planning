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


def _resolve_api_base() -> str:
    if "api_base" in st.secrets:
        return st.secrets["api_base"]
    return os.environ.get("NP_PLANNING_API_BASE", DEFAULT_API_BASE)


API_BASE = _resolve_api_base()

st.set_page_config(page_title="NP Planning -- manual test UI", layout="wide")
st.title("NP Planning -- manual test UI")
st.caption(
    f"Talking to {API_BASE}. This is a thin HTTP test client for the backend, not the real "
    "Customer Mode product UI."
)

_STATE_KEYS = [
    "token", "last_project_id", "last_quote_id", "last_opportunity_id", "last_spec_id",
    "last_site_id", "last_flag_id", "last_branch_id", "last_page_id", "last_recipe_id",
    "last_product_id", "last_supplier_id", "last_supplier_quote_id",
]
for key in _STATE_KEYS:
    if key not in st.session_state:
        st.session_state[key] = None


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}


def call(method: str, path: str, **kwargs):
    try:
        response = requests.request(method, f"{API_BASE}{path}", headers=auth_headers(), timeout=15, **kwargs)
    except requests.exceptions.ConnectionError:
        st.error(f"Could not reach {API_BASE} -- is the backend running and reachable from here?")
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
    st.header("Login")
    if st.session_state.token:
        st.success("Logged in")
        if st.button("Log out"):
            requests.post(f"{API_BASE}/auth/logout", headers=auth_headers())
            st.session_state.token = None
            st.rerun()
    else:
        email = st.text_input("Email", value=st.secrets.get("default_email", ""))
        password = st.text_input("Password", type="password", value=st.secrets.get("default_password", ""))
        if st.button("Log in"):
            response = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
            if response.status_code == 200:
                st.session_state.token = response.json()["token"]
                st.rerun()
            else:
                st.error(f"{response.status_code}: {response.text}")
    st.divider()
    st.caption("Site ID used as the default across tabs (paste a real one)")
    st.session_state.last_site_id = st.text_input(
        "Default Site ID", value=st.session_state.last_site_id or "", key="default_site_id_input"
    )

if not st.session_state.token:
    st.info("Log in from the sidebar to test the protected endpoints.")
    st.stop()

(
    tab_sites, tab_canopy, tab_confirm, tab_business, tab_opportunities, tab_specs, tab_quality,
    tab_knowledge, tab_website, tab_products, tab_recipes, tab_suppliers, tab_raw,
) = st.tabs(
    [
        "Sites", "Canopy configurator", "Confirm quote", "Business health", "Opportunities",
        "Critical specs", "Site quality", "Site knowledge", "Website studio", "Products",
        "Recipes", "Suppliers", "Raw API call",
    ]
)

with tab_sites:
    st.subheader("POST /sites")
    st.caption("Most other tabs need a Site ID -- create one here first. customer_name is get-or-create.")
    customer_name = st.text_input("Customer name", value="Test Customer")
    site_type = st.selectbox("Site type", ["HOME", "OFFICE", "FACTORY"])
    site_name = st.text_input("Site name", value="Test Site")
    site_address = st.text_input("Address (optional)", value="")
    if st.button("Create site"):
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
    site_id = st.text_input("Site ID", value=st.session_state.last_site_id or "")
    col1, col2 = st.columns(2)
    width_m = col1.number_input("Width (m)", value=6.0, min_value=0.1)
    length_m = col2.number_input("Length (m)", value=4.0, min_value=0.1)
    roof_cover = st.selectbox("Roof cover", ["Metal Sheet", "Polycarbonate", "Vinyl", "D-Lite", "Shinkolite"])
    unit_cost_per_m2 = st.number_input("Unit cost per m2 (manual)", value=1500.0, min_value=0.0)

    if st.button("Configure canopy"):
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
    st.caption("Every canopy quote's gate is OVERRIDE_REQUIRED (placeholder quantity basis, C3) -- an override_reason is required.")
    project_id = st.text_input("Project ID", value=st.session_state.last_project_id or "")
    quote_id = st.text_input("Quote ID", value=st.session_state.last_quote_id or "")
    confirmed_by = st.text_input("Confirmed by", value="Test Admin")
    override_reason = st.text_input("Override reason", value="Manual test confirmation")

    if st.button("Confirm quote"):
        call(
            "POST", "/quotes/confirm",
            json={
                "project_id": project_id, "quote_id": quote_id,
                "confirmed_by": confirmed_by, "override_reason": override_reason or None,
            },
        )

    if quote_id:
        st.divider()
        st.caption("What-if (POST /quotes/{id}/what-if)")
        wcol1, wcol2 = st.columns(2)
        cost_change = wcol1.number_input("Cost change %", value=8.0)
        if wcol1.button("Simulate cost change"):
            call("POST", f"/quotes/{quote_id}/what-if", json={"cost_change_percent": cost_change})
        discount = wcol2.number_input("Discount %", value=5.0)
        if wcol2.button("Simulate discount"):
            call("POST", f"/quotes/{quote_id}/what-if", json={"discount_percent": discount})

        st.caption("Recommendations (GET /quotes/{id}/recommendations)")
        if st.button("Fetch recommendations"):
            call("GET", f"/quotes/{quote_id}/recommendations")

with tab_business:
    st.subheader("GET /business/health")
    as_of = st.text_input("as_of (ISO datetime, optional)", value="")
    if st.button("Refresh dashboard"):
        params = {"as_of": as_of} if as_of else None
        call("GET", "/business/health", params=params)

with tab_opportunities:
    st.subheader("POST /opportunities")
    opp_site_id = st.text_input("Site ID", value=st.session_state.last_site_id or "", key="opp_site_id")
    source = st.selectbox("Source", ["website_inquiry", "referral", "repeat_customer"])
    description = st.text_input("Description", value="Manual test opportunity")
    if st.button("Create opportunity"):
        body = call("POST", "/opportunities", json={"site_id": opp_site_id, "source": source, "description": description})
        if body:
            st.session_state.last_opportunity_id = body["id"]

    st.divider()
    st.caption("POST /opportunities/{id}/convert")
    opportunity_id = st.text_input("Opportunity ID", value=st.session_state.last_opportunity_id or "")
    project_data = st.text_area("Project data (JSON)", value='{"name": "Converted from opportunity"}')
    if st.button("Convert to project"):
        try:
            parsed = json.loads(project_data)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
        else:
            body = call("POST", f"/opportunities/{opportunity_id}/convert", json={"project_data": parsed})
            if body:
                st.session_state.last_project_id = body["project_id"]

with tab_specs:
    st.subheader("POST /critical-specs")
    spec_project_id = st.text_input("Project ID", value=st.session_state.last_project_id or "", key="spec_project_id")
    spec_type = st.text_input("Spec type", value="roof_material_model")
    spec_description = st.text_input("Description", value="TBD")
    if st.button("Create critical spec"):
        body = call("POST", "/critical-specs", json={"project_id": spec_project_id, "spec_type": spec_type, "description": spec_description})
        if body:
            st.session_state.last_spec_id = body["id"]

    st.divider()
    st.caption("POST /critical-specs/{id}/transition")
    spec_id = st.text_input("Critical Spec ID", value=st.session_state.last_spec_id or "")
    to_state = st.selectbox("Transition to", ["PROPOSED", "CONFIRMED"])
    spec_confirmed_by = st.text_input("Confirmed by (only used for CONFIRMED)", value="Estimator J.")
    if st.button("Transition spec"):
        call("POST", f"/critical-specs/{spec_id}/transition", json={"to_state": to_state, "confirmed_by": spec_confirmed_by})

with tab_quality:
    st.subheader("POST /sites/{id}/quality-flags")
    quality_site_id = st.text_input("Site ID", value=st.session_state.last_site_id or "", key="quality_site_id")
    flag_type = st.selectbox(
        "Flag type",
        ["BAD_PAYMENT", "REPEATED_SCOPE_ABUSE", "MARGIN_LEAKAGE", "HIGH_DISPUTE", "EXCESSIVE_ADMIN_BURDEN", "UNSAFE_PRACTICES", "POOR_CAPACITY_FIT"],
    )
    flag_description = st.text_input("Description", value="Manual test flag")
    flagged_by = st.text_input("Flagged by", value="PM K.")
    if st.button("Flag site"):
        body = call(
            "POST", f"/sites/{quality_site_id}/quality-flags",
            json={"flag_type": flag_type, "description": flag_description, "flagged_by": flagged_by},
        )
        if body:
            st.session_state.last_flag_id = body["id"]

    st.divider()
    if st.button("Check site health"):
        call("GET", f"/sites/{quality_site_id}/quality")

    st.divider()
    flag_id = st.text_input("Flag ID to resolve", value=st.session_state.last_flag_id or "")
    if st.button("Resolve flag"):
        call("POST", f"/quality-flags/{flag_id}/resolve")

with tab_knowledge:
    st.subheader("GET /sites/{id}/knowledge")
    knowledge_site_id = st.text_input("Site ID", value=st.session_state.last_site_id or "", key="knowledge_site_id")
    if st.button("Fetch observations"):
        call("GET", f"/sites/{knowledge_site_id}/knowledge")

    st.divider()
    st.caption("GET /sites/{id}/survey-checklist")
    knowledge_types = st.text_input("Knowledge types (comma-separated)", value="pile_depth,soil_bearing")
    if st.button("Fetch survey checklist"):
        call("GET", f"/sites/{knowledge_site_id}/survey-checklist", params={"knowledge_types": knowledge_types})

with tab_website:
    st.subheader("POST /website/branches")
    branch_name = st.text_input("Branch name", value="MAIN")
    if st.button("Create branch"):
        body = call("POST", "/website/branches", json={"name": branch_name})
        if body:
            st.session_state.last_branch_id = body["id"]

    st.divider()
    st.caption("POST /website/pages")
    branch_id = st.text_input("Branch ID", value=st.session_state.last_branch_id or "")
    slug = st.text_input("Slug", value="home")
    widget_type = st.text_input("Widget type", value="Hero")
    if st.button("Create page"):
        body = call(
            "POST", "/website/pages",
            json={"branch_id": branch_id, "slug": slug, "widgets": [{"widget_type": widget_type, "order_index": 0}]},
        )
        if body:
            st.session_state.last_page_id = body["page_id"]

    st.divider()
    st.caption("PUT /website/pages/{id}")
    page_id = st.text_input("Page ID", value=st.session_state.last_page_id or "")
    new_widget_type = st.text_input("New widget type", value="ServiceCards")
    if st.button("Update page"):
        call("PUT", f"/website/pages/{page_id}", json={"widgets": [{"widget_type": new_widget_type, "order_index": 0}]})

    st.divider()
    st.caption("POST /website/pages/{id}/restore")
    restore_to = st.number_input("Restore to revision number", value=1, min_value=1, step=1)
    if st.button("Restore revision"):
        call("POST", f"/website/pages/{page_id}/restore", json={"target_revision_number": int(restore_to)})

with tab_products:
    st.subheader("GET /products")
    if st.button("List products"):
        body = call("GET", "/products")
        if body:
            st.session_state.last_product_id = body[0]["id"] if body else None

with tab_recipes:
    st.subheader("POST /recipes")
    st.caption("Needs a real Product ID -- fetch one from the Products tab, or create one via the canopy configurator (which auto-creates the CANOPY product).")
    product_id = st.text_input("Product ID", value=st.session_state.last_product_id or "")
    recipe_name = st.text_input("Recipe name", value="Standard")
    formula_text = st.text_area("Formula (JSON)", value='{"waste_factor": 0.05}')
    if st.button("Create recipe"):
        try:
            formula = json.loads(formula_text)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
        else:
            body = call("POST", "/recipes", json={"product_id": product_id, "name": recipe_name, "formula": formula})
            if body:
                st.session_state.last_recipe_id = body["recipe_id"]

    st.divider()
    recipe_id = st.text_input("Recipe ID", value=st.session_state.last_recipe_id or "")
    new_formula_text = st.text_area("New formula (JSON)", value='{"waste_factor": 0.08}')
    if st.button("Update recipe"):
        try:
            new_formula = json.loads(new_formula_text)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
        else:
            call("PUT", f"/recipes/{recipe_id}", json={"formula": new_formula})

    st.divider()
    restore_version = st.number_input("Restore to version number", value=1, min_value=1, step=1)
    if st.button("Restore recipe version"):
        call("POST", f"/recipes/{recipe_id}/restore", json={"target_version_number": int(restore_version)})

with tab_suppliers:
    st.subheader("POST /suppliers")
    supplier_name = st.text_input("Supplier name", value="Supplier A")
    if st.button("Create supplier"):
        body = call("POST", "/suppliers", json={"name": supplier_name})
        if body:
            st.session_state.last_supplier_id = body["id"]

    st.divider()
    st.caption("POST /suppliers/quotes")
    supplier_id = st.text_input("Supplier ID", value=st.session_state.last_supplier_id or "")
    material_description = st.text_input("Material description", value="Metal Sheet Roofing, 0.35mm")
    qcol1, qcol2, qcol3 = st.columns(3)
    quoted_price = qcol1.number_input("Quoted price", value=98.0)
    validity_days = qcol2.number_input("Validity (days)", value=14, step=1)
    lock_days = qcol3.number_input("Lock (days)", value=30, step=1)
    lead_time_days = st.number_input("Lead time (days)", value=21, step=1)
    quote_date = st.date_input("Quote date")
    if st.button("Create supplier quote"):
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
    st.caption("POST /suppliers/quotes/{id}/actual-procurement")
    supplier_quote_id = st.text_input("Supplier Quote ID", value=st.session_state.last_supplier_quote_id or "")
    actual_price = st.number_input("Actual price", value=99.5)
    actual_lead_time = st.number_input("Actual lead time (days)", value=25, step=1)
    if st.button("Record actual procurement"):
        call(
            "POST", f"/suppliers/quotes/{supplier_quote_id}/actual-procurement",
            json={"actual_price": actual_price, "actual_lead_time_days": int(actual_lead_time)},
        )

with tab_raw:
    st.subheader("Any endpoint")
    method = st.selectbox("Method", ["GET", "POST", "PUT"])
    path = st.text_input("Path", value="/business/health")
    body_text = st.text_area("JSON body (for POST/PUT)", value="{}")
    if st.button("Send"):
        try:
            body = json.loads(body_text) if body_text.strip() else None
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
        else:
            call(method, path, json=body)
