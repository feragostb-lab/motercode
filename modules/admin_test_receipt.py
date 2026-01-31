"""Page to test OCR processing with a single receipt image."""
from pathlib import Path
import json
import tempfile
from typing import Any, Callable, Optional

import streamlit as st

from src.ocr_processor import BackgroundOCRProcessor

_ALLOWED_IMAGE_TYPES = ["png", "jpg", "jpeg", "bmp", "webp", "tif", "tiff"]


def _get_test_processor() -> BackgroundOCRProcessor:
    if "admin_test_processor" not in st.session_state:
        st.session_state.admin_test_processor = BackgroundOCRProcessor()
    return st.session_state.admin_test_processor


def render() -> None:
    st.title("🧪 Test de OCR de Recibos")
    st.caption("Carga una imagen y ejecuta el OCR sin guardar los resultados en la base de datos.")

    uploaded_file = st.file_uploader(
        "Selecciona una imagen de recibo",
        type=_ALLOWED_IMAGE_TYPES,
        help="Sólo se procesa localmente y no se registran los resultados.",
        accept_multiple_files=False
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        st.image(file_bytes, use_container_width=True)
        st.markdown(f"**Archivo:** {uploaded_file.name} · {len(file_bytes) / 1024:.1f} KB")

        suffix = Path(uploaded_file.name).suffix or ".jpg"

        if st.button("🚀 Ejecutar OCR de prueba", type="primary", key="run_admin_test_receipt"):
            with st.spinner("Analizando imagen con el modelo..."):
                temp_path: Optional[Path] = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(file_bytes)
                        temp_path = Path(tmp.name)

                    processor = _get_test_processor()
                    result = processor.analyze_image_for_test(str(temp_path))
                    st.session_state.admin_test_receipt_result = result
                    st.success("OCR completado (resultado de prueba, no se persiste)")
                except Exception as exc:
                    st.session_state.pop("admin_test_receipt_result", None)
                    st.error(f"Error al procesar la imagen: {exc}")
                finally:
                    if temp_path and temp_path.exists():
                        temp_path.unlink()
    else:
        st.info("Carga una imagen para ejecutar el OCR de forma aislada.")

    result: Optional[dict[str, Any]] = st.session_state.get("admin_test_receipt_result")
    if result:
        st.divider()
        st.subheader("📊 Clasificación y datos extraídos")

        st.metric("Tipo deducido", result.get("deduced_type") or "N/A")

        detected = result.get("detected_categories") or []
        st.caption("Categorías detectadas (Stage 1)")
        if detected:
            st.write(", ".join(detected))
        else:
            st.write("Ninguna categoría marcada con indicadores directos")

        fields = result.get("final_fields") or {}
        if fields:
            st.caption("Campos normalizados utilizados para la clasificación")
            display_rows = [
                {
                    "Campo": key,
                    "Valor": (
                        value
                        if isinstance(value, str)
                        else json.dumps(value, ensure_ascii=False)
                    )
                }
                for key, value in sorted(fields.items())
            ]
            st.table(display_rows)
        else:
            st.info("El modelo no devolvió campos normalizados.")

        auxiliary = result.get("auxiliary_fields") or {}
        if auxiliary:
            st.subheader("🧠 Campos auxiliares (Stage 2)")
            display_aux = [
                {"Campo": key, "Valor": value}
                for key, value in sorted(auxiliary.items())
            ]
            st.table(display_aux)

        st.subheader("🛰️ Respuesta del modelo")
        st.caption("JSON completo que devolvió el modelo en Stage 1")
        st.code(result.get("model_response", ""), language="json")

    if st.button("🧹 Limpiar resultados", key="clear_admin_test_receipt"):
        st.session_state.pop("admin_test_receipt_result", None)
        _rerun()

def _rerun() -> None:
    rerun_fn: Optional[Callable[[], None]] = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun_fn:
        rerun_fn()
