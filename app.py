import streamlit as st
from supabase import create_client
from datetime import datetime, timezone

# -----------------------------
# Supabase client (Cloud secrets)
# -----------------------------
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# -----------------------------
# Session State
# -----------------------------
if "address" not in st.session_state:
    st.session_state.address = ""
if "units_list" not in st.session_state:
    st.session_state.units_list = []
if "current_unit" not in st.session_state:
    st.session_state.current_unit = None

# -----------------------------
# Functions
# -----------------------------
def load_units(address):
    """Adresin taşıma birimlerini Supabase'den yükle"""
    response = supabase.table("stock_units").select("*").eq("address", address).execute()
    return response.data if response.data else []

def next_unit():
    """Bir sonraki okutulacak HU'yu belirle"""
    for unit in st.session_state.units_list:
        if not unit.get("counted", False):
            st.session_state.current_unit = unit
            return
    st.session_state.current_unit = None

def reset_address():
    st.session_state.address = ""
    st.session_state.units_list = []
    st.session_state.current_unit = None

# -----------------------------
# UI: Adres Barkodu
# -----------------------------
st.title("📦 Yarım Kutu Sayım")

if not st.session_state.address:
    address_input = st.text_input("Adres Barkodu")
    if address_input:
        st.session_state.address = address_input
        st.session_state.units_list = load_units(address_input)
        next_unit()
else:
    st.write(f"📍 Adres: **{st.session_state.address}**")
    st.write(f"Toplam HU sayısı: {len(st.session_state.units_list)}")
    counted = sum(1 for u in st.session_state.units_list if u.get("counted"))
    st.write(f"Sayılan HU: {counted} / {len(st.session_state.units_list)}")

# -----------------------------
# UI: HU Barkodu
# -----------------------------
if st.session_state.current_unit:
    unit = st.session_state.current_unit

    st.info("🔍 Bulunan Taşıma Birimi")
    st.write(f"**Malzeme:** {unit['material']}")
    st.write(f"**Lot:** {unit['lot']}")
    st.write(f"**Miktar:** {unit['qty']}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ ONAYLA"):
            supabase.table("stock_units").update({
                "counted": True,
                "status": "ok",
                "counted_at": datetime.now(timezone.utc).isoformat()  # JSON uyumlu
            }).eq("id", unit["id"]).execute()

            next_unit()
            st.experimental_rerun()

    with col2:
        if st.button("❌ RED"):
            st.session_state.current_unit = None
            st.warning("Lütfen doğru HU'yu okutun")

else:
    st.info("✅ Tüm HU’lar sayıldı veya adres seçin")

# -----------------------------
# UI: Adres Kontrolü Bitti
# -----------------------------
if st.session_state.address and st.button("📌 Adres Kontrolü Bitti"):
    missing = supabase.table("stock_units") \
        .select("id") \
        .eq("address", st.session_state.address) \
        .eq("counted", False) \
        .execute()

    if missing.data:
        ids = [x["id"] for x in missing.data]

        supabase.table("stock_units").update({
            "status": "missing",
            "counted_at": datetime.now(timezone.utc).isoformat()
        }).in_("id", ids).execute()

        st.warning(f"⚠️ {len(ids)} adet taşıma birimi BULUNAMADI olarak işaretlendi")

    st.success("✅ Adres tamamlandı")
    st.button("➡️ Yeni Adrese Geç", on_click=reset_address)
