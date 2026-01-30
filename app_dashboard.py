"""Streamlit dashboard for receipt review and management."""
import streamlit as st
from pathlib import Path
import sys
from PIL import Image

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import get_config
from src.services.receipt_service import ReceiptService
from src.services.bank_matching_service import BankMatchingService
from src.services.statistics_service import StatisticsService
from src.services.export_service import ExportService
from src.repositories.ignored_repository import IgnoredRepository
from src.repositories.period_repository import PeriodRepository
from src.core.database import get_database
from src.core.logging import setup_logging
from src.core.backup_manager import BackupManager
from src.models.domain import Match, MatchType
import os
from datetime import datetime


def init_session_state():
    """Initialize session state variables."""
    if 'config' not in st.session_state:
        st.session_state.config = get_config()
    
    if 'receipt_service' not in st.session_state:
        config = st.session_state.config
        st.session_state.receipt_service = ReceiptService(config)
        st.session_state.matching_service = BankMatchingService(config)
        st.session_state.stats_service = StatisticsService(config)
        st.session_state.export_service = ExportService(config)
    
    # Initialize ignored_repo separately to handle system resets
    if 'ignored_repo' not in st.session_state:
        config = st.session_state.config
        db = get_database(config.paths.get('database'))
        st.session_state.ignored_repo = IgnoredRepository(db)
    
    # Initialize period_repo for multi-worker support
    if 'period_repo' not in st.session_state:
        config = st.session_state.config
        db = get_database(config.paths.get('database'))
        st.session_state.period_repo = PeriodRepository(db)
    
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    
    if 'filter_type' not in st.session_state:
        st.session_state.filter_type = 'all'
    
    if 'filter_match' not in st.session_state:
        st.session_state.filter_match = 'all'
    
    # Sorting state for receipts
    if 'sort_by' not in st.session_state:
        st.session_state.sort_by = None  # None, 'date', 'amount', or 'id'
    
    if 'sort_order' not in st.session_state:
        st.session_state.sort_order = 'asc'  # 'asc' or 'desc'

    # Index for navigating unmatched receipts on Bank Transactions page
    if 'unmatched_index' not in st.session_state:
        st.session_state.unmatched_index = 0

    # Current navigation page selection for sidebar
    if 'nav_page' not in st.session_state:
        st.session_state.nav_page = "Bank Transactions"


def page_receipts():
    """Receipt review page."""
    st.header("📄 Receipt Review")
    
    receipt_service = st.session_state.receipt_service
    matching_service = st.session_state.matching_service
    ignored_repo = st.session_state.ignored_repo
    period_repo = st.session_state.period_repo
    
    # Get active period if exists
    active_period = period_repo.get_active_processing_period()
    
    # Get receipts (filtered by active period if exists)
    if active_period:
        all_receipts = receipt_service.repository.get_by_period(active_period.id)
    else:
        all_receipts = receipt_service.repository.get_all()
    
    # Apply filters
    filtered_receipts = all_receipts
    if st.session_state.filter_type != 'all':
        filtered_receipts = [r for r in filtered_receipts if r.receipt_type == st.session_state.filter_type]
    if st.session_state.filter_match == 'matched':
        matched_ids = {m.receipt_id for m in matching_service.match_repo.get_all() if m.match_type.value != 'unmatched'}
        filtered_receipts = [r for r in filtered_receipts if r.id in matched_ids]
    elif st.session_state.filter_match == 'unmatched':
        matched_ids = {m.receipt_id for m in matching_service.match_repo.get_all() if m.match_type.value != 'unmatched'}
        filtered_receipts = [r for r in filtered_receipts if r.id not in matched_ids]
    elif st.session_state.filter_match == 'conflicts':
        conflict_ids = {m.receipt_id for m in matching_service.match_repo.get_all() if m.is_conflict}
        filtered_receipts = [r for r in filtered_receipts if r.id in conflict_ids]
    
    if not st.session_state.get('show_ignored', False):
        ignored_ids = {i.receipt_id for i in ignored_repo.get_all()}
        filtered_receipts = [r for r in filtered_receipts if r.id not in ignored_ids]
    
    # Apply sorting
    if st.session_state.sort_by:
        sort_key = st.session_state.sort_by
        reverse = st.session_state.sort_order == 'desc'
        
        if sort_key == 'id':
            # Receipts with ID first, then without ID at the end
            receipts_with_id = [r for r in filtered_receipts if r.id is not None]
            receipts_without_id = [r for r in filtered_receipts if r.id is None]
            receipts_with_id.sort(key=lambda x: x.id, reverse=reverse)
            filtered_receipts = receipts_with_id + receipts_without_id
        elif sort_key == 'date':
            # Receipts with date first, then without date at the end
            receipts_with_date = [r for r in filtered_receipts if r.date is not None]
            receipts_without_date = [r for r in filtered_receipts if r.date is None]
            receipts_with_date.sort(key=lambda x: x.date, reverse=reverse)
            filtered_receipts = receipts_with_date + receipts_without_date
        elif sort_key == 'amount':
            # Receipts with amount first, then without amount at the end
            receipts_with_amount = [r for r in filtered_receipts if r.amount is not None]
            receipts_without_amount = [r for r in filtered_receipts if r.amount is None]
            receipts_with_amount.sort(key=lambda x: x.amount, reverse=reverse)
            filtered_receipts = receipts_with_amount + receipts_without_amount

    # Check if we need to navigate to a specific receipt ID
    if 'navigate_to_receipt_id' in st.session_state:
        target_id = st.session_state.navigate_to_receipt_id
        del st.session_state.navigate_to_receipt_id
        
        # Try to find the receipt in filtered list
        found_index = next((i for i, r in enumerate(filtered_receipts) if r.id == target_id), None)
        if found_index is not None:
            st.session_state.current_index = found_index
        else:
            print("Receipt not found in current filter, trying to clear filters")
            # Receipt not in current filter, clear filters and try again
            st.session_state.filter_type = 'all'
            st.session_state.filter_match = 'all'
            # Reapply filters
            filtered_receipts = all_receipts
            if not st.session_state.get('show_ignored', False):
                ignored_ids = {i.receipt_id for i in ignored_repo.get_all()}
                filtered_receipts = [r for r in filtered_receipts if r.id not in ignored_ids]
            # Find receipt again
            found_index = next((i for i, r in enumerate(filtered_receipts) if r.id == target_id), 0)
            st.session_state.current_index = found_index
    
    # Bound current_index
    if not filtered_receipts:
        st.warning("No receipts found matching filters.")
    else:    
        if st.session_state.current_index >= len(filtered_receipts):
            st.session_state.current_index = len(filtered_receipts) - 1
        if st.session_state.current_index < 0:
            st.session_state.current_index = 0
        
        current_receipt = filtered_receipts[st.session_state.current_index]
        
        # Layout: Image on left, details on right
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Sorting buttons
            sort_col1, sort_col2, sort_col3, sort_col4 = st.columns([1, 1, 1, 2])
            
            with sort_col1:
                # Date sort button
                if st.session_state.sort_by == 'date':
                    arrow = '↓' if st.session_state.sort_order == 'asc' else '↑'
                    button_label = f"📅 Fecha {arrow}"
                else:
                    button_label = "📅 Fecha"
                
                if st.button(button_label, key="sort_date_btn"):
                    if st.session_state.sort_by == 'date':
                        # Toggle order
                        st.session_state.sort_order = 'desc' if st.session_state.sort_order == 'asc' else 'asc'
                    else:
                        # Set new sort
                        st.session_state.sort_by = 'date'
                        st.session_state.sort_order = 'asc'
                    st.rerun()
            
            with sort_col2:
                # Amount sort button
                if st.session_state.sort_by == 'amount':
                    arrow = '↓' if st.session_state.sort_order == 'asc' else '↑'
                    button_label = f"💰 Importe {arrow}"
                else:
                    button_label = "💰 Importe"
                
                if st.button(button_label, key="sort_amount_btn"):
                    if st.session_state.sort_by == 'amount':
                        # Toggle order
                        st.session_state.sort_order = 'desc' if st.session_state.sort_order == 'asc' else 'asc'
                    else:
                        # Set new sort
                        st.session_state.sort_by = 'amount'
                        st.session_state.sort_order = 'asc'
                    st.rerun()
            
            with sort_col3:
                # ID sort button
                if st.session_state.sort_by == 'id':
                    arrow = '↓' if st.session_state.sort_order == 'asc' else '↑'
                    button_label = f"🔢 ID {arrow}"
                else:
                    button_label = "🔢 ID"
                
                if st.button(button_label, key="sort_id_btn"):
                    if st.session_state.sort_by == 'id':
                        # Toggle order
                        st.session_state.sort_order = 'desc' if st.session_state.sort_order == 'asc' else 'asc'
                    else:
                        # Set new sort
                        st.session_state.sort_by = 'id'
                        st.session_state.sort_order = 'asc'
                    st.rerun()
            
            with sort_col4:
                # Clear sort button
                if st.session_state.sort_by:
                    if st.button("❌ Limpiar orden", key="clear_sort_btn"):
                        st.session_state.sort_by = None
                        st.session_state.sort_order = 'asc'
                        st.rerun()
            
            st.divider()
            
            # Navigation buttons
            nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
            with nav_col1:
                if st.button("⏮️ First"):
                    st.session_state.current_index = 0
                    st.rerun()
            with nav_col2:
                if st.button("◀️ Previous"):
                    if st.session_state.current_index > 0:
                        st.session_state.current_index -= 1
                        st.rerun()
            with nav_col3:
                if st.button("▶️ Next"):
                    if st.session_state.current_index < len(filtered_receipts) - 1:
                        st.session_state.current_index += 1
                        st.rerun()
            with nav_col4:
                if st.button("⏭️ Last"):
                    st.session_state.current_index = len(filtered_receipts) - 1
                    st.rerun()

            st.subheader(f"Image ({st.session_state.current_index + 1}/{len(filtered_receipts)})")
            
            # Display image
            if current_receipt.file_path and Path(current_receipt.file_path).exists():
                try:
                    img = Image.open(current_receipt.file_path)
                    st.image(img, width='stretch')
                except Exception as e:
                    st.error(f"Failed to load image: {e}")
            else:
                st.warning("Image file not found")
            
           
        
        with col2:
            st.subheader("Details")
            
            # Display current details
            st.write(f"**File:** {Path(current_receipt.file_path).name if current_receipt.file_path else 'N/A'}")
            st.write(f"**Type:** {current_receipt.receipt_type or 'Unknown'}")
            st.write(f"**Date:** {current_receipt.date.strftime('%d-%m-%Y') if current_receipt.date else 'N/A'}")
            st.write(f"**Amount:** €{current_receipt.amount:.2f}" if current_receipt.amount else "**Amount:** N/A")
            st.write(f"**Processed:** {current_receipt.created_at.strftime('%d-%m-%Y %H:%M') if current_receipt.created_at else 'N/A'}")
            
            # Extracted data in collapsible panel
            if current_receipt.extracted_data:
                with st.expander("📋 Model Extracted Information", expanded=False):
                    import json
                    extracted_text = json.dumps(current_receipt.extracted_data, indent=2, ensure_ascii=False)
                    st.code(extracted_text, language="json")
            
            st.divider()
            
            # Edit form
            st.subheader("Edit")
            
            # Type selector
            receipt_types = st.session_state.config.receipt_types
            type_index = receipt_types.index(current_receipt.receipt_type) if current_receipt.receipt_type in receipt_types else 0
            selected_type = st.selectbox("Type", receipt_types, index=type_index, key=f"type_{current_receipt.id}")
            
            # Date input with range (today to 5 years ago)
            from datetime import date, timedelta
            today = date.today()
            five_years_ago = today - timedelta(days=5*365)
            
            # Validate current receipt date is within range, otherwise use today
            receipt_date = current_receipt.date
            if receipt_date:
                if receipt_date.date() < five_years_ago or receipt_date.date() > today:
                    receipt_date = today
                else:
                    receipt_date = receipt_date.date()
            else:
                receipt_date = today
            
            selected_date = st.date_input(
                "Date", 
                value=receipt_date, 
                min_value=five_years_ago,
                max_value=today,
                key=f"date_{current_receipt.id}"
            )
            
            # Amount input
            selected_amount = st.number_input("Amount", min_value=0.0, step=0.01, value=float(current_receipt.amount) if current_receipt.amount else 0.0, key=f"amount_{current_receipt.id}")
            
            # Description input
            selected_description = st.text_area("Receipt Description", value=current_receipt.description or '', key=f"desc_{current_receipt.id}", height=80)
            
            if st.button("💾 Save Changes"):
                try:
                    receipt_service.update_receipt_type(current_receipt.id, selected_type)
                    receipt_service.update_receipt_date(current_receipt.id, selected_date)
                    receipt_service.update_receipt_amount(current_receipt.id, selected_amount)
                    receipt_service.update_receipt_description(current_receipt.id, selected_description)
                    st.success("Changes saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save: {e}")
            
            st.divider()
            
            # Actions
            is_ignored = ignored_repo.is_ignored(current_receipt.id)
            if is_ignored:
                if st.button("↩️ Unignore Receipt"):
                    ignored_repo.unignore_receipt(current_receipt.id)
                    # Recalculate conflicts after unignoring
                    matching_service.recompute_conflict_flags()
                    # Switch to normal view (hide ignored) so user sees the receipt in the main list
                    st.session_state.show_ignored = False
                    st.success("Receipt restored")
                    st.rerun()
            else:
                if st.button("🗑️ Ignore Receipt"):
                    ignored_repo.ignore_receipt(current_receipt.id, "Manually ignored")
                    # Recalculate conflicts after ignoring
                    matching_service.recompute_conflict_flags()
                    st.success("Receipt ignored")
                    st.rerun()
            
            # Match info
            st.subheader("Bank Match")
            match = matching_service.match_repo.get_by_receipt_id(current_receipt.id)
            if match:
                st.write(f"**Match Type:** {match.match_type.value}")
                st.write(f"**Confidence:** {match.confidence:.1%}")
                if match.transaction_id:
                    bank_txn = matching_service.bank_repo.get_by_id(match.transaction_id)
                    if bank_txn:
                        st.write(f"**Bank Date:** {bank_txn.date.strftime('%d-%m-%Y')}")
                        st.write(f"**Bank Amount:** €{bank_txn.amount:.2f}")
                        st.write(f"**Description:** {bank_txn.description or 'N/A'}")
                
                if match.is_conflict:
                    st.warning("⚠️ Conflict detected")
                    
                    # Get conflicting receipts
                    conflicting_ids = matching_service.get_conflicting_receipts(current_receipt.id)
                    
                    if conflicting_ids:
                        st.write(f"**{len(conflicting_ids)} other receipt(s) in conflict:**")
                        
                        # Show buttons to navigate to conflicting receipts
                        cols = st.columns(min(len(conflicting_ids), 4))
                        for idx, conflict_id in enumerate(conflicting_ids):
                            conflict_receipt = receipt_service.get_receipt_by_id(conflict_id)
                            if conflict_receipt:
                                col_idx = idx % 4
                                with cols[col_idx]:
                                    button_label = f"📄 Receipt #{conflict_id}"
                                    if st.button(button_label, key=f"goto_conflict_{conflict_id}"):
                                        st.session_state.navigate_to_receipt_id = conflict_id
                                        st.rerun()
                    
                    st.divider()
                    if st.button("✅ Accept Conflict", key=f"accept_{match.id}"):
                        matching_service.match_repo.accept_conflict(match.receipt_id)
                        # Recalculate conflicts after accepting
                        matching_service.recompute_conflict_flags()
                        st.success("Conflict accepted")
                        st.rerun()
            else:
                st.info("No bank match found")
    
    # Filters sidebar
    with st.sidebar:
        receipt_types = st.session_state.config.receipt_types
        st.subheader("🔍 Filters")

        # Calculate current index for Type filter
        filter_options = ['all'] + receipt_types
        try:
            current_type_index = filter_options.index(st.session_state.filter_type)
        except ValueError:
            current_type_index = 0
        
        filter_type = st.selectbox(
            "Type",
            filter_options,
            index=current_type_index
        )
        if filter_type != st.session_state.filter_type:
            st.session_state.filter_type = filter_type
            st.session_state.current_index = 0  # Reset to first
            st.rerun()
        
        # Calculate current index for Match Status filter
        match_options = ['all', 'matched', 'unmatched', 'conflicts']
        try:
            current_match_index = match_options.index(st.session_state.filter_match)
        except ValueError:
            current_match_index = 0
        
        filter_match = st.selectbox(
            "Match Status",
            match_options,
            index=current_match_index
        )
        if filter_match != st.session_state.filter_match:
            st.session_state.filter_match = filter_match
            st.session_state.current_index = 0  # Reset to first
            st.rerun()
        
        show_ignored = st.checkbox("Show Ignored", value=st.session_state.get('show_ignored', False))
        if show_ignored != st.session_state.get('show_ignored', False):
            st.session_state.show_ignored = show_ignored
            st.session_state.current_index = 0  # Reset to first
            st.rerun()


def page_bank_transactions():
    """Bank transactions page."""
    st.header("🏦 Bank Transactions")
    
    # Initialize session state for detach selections
    if 'selected_detach' not in st.session_state:
        st.session_state.selected_detach = set()
    
    # Add refresh button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    matching_service = st.session_state.matching_service
    receipt_service = st.session_state.receipt_service
    period_repo = st.session_state.period_repo
    active_period = period_repo.get_active_processing_period()
    period_id = active_period.id if active_period else None

    # Load bank transactions (fresh from database)
    if period_id:
        transactions = matching_service.bank_repo.get_by_period(period_id)
    else:
        transactions = matching_service.bank_repo.get_all()
    
    if active_period:
        st.caption(f"Active Period: {active_period.month_year}")

    if not transactions:
        period_note = f" for period {active_period.month_year}" if active_period else ""
        st.warning(f"No bank transactions found{period_note}. Load transactions from Excel first.")
        
        if st.button("📂 Load from Excel"):
            try:
                config = st.session_state.config
                excel_path = config.paths.get('bank_excel')
                if excel_path and Path(excel_path).exists():
                    count = matching_service.bank_repo.load_from_excel(excel_path)
                    st.success(f"Loaded {count} transactions from Excel")
                    st.rerun()
                else:
                    st.error(f"Excel file not found: {excel_path}")
            except Exception as e:
                st.error(f"Failed to load Excel: {e}")
        return
    
    # Get matches relevant to the current view (filtered by period if active)
    all_matches = matching_service.match_repo.get_all()
    if period_id:
        period_txn_ids = {txn.id for txn in transactions}
        filtered_matches = [m for m in all_matches if m.transaction_id in period_txn_ids]
    else:
        filtered_matches = all_matches

    match_by_bank_id = {}
    for match in filtered_matches:
        if match.transaction_id:
            match_by_bank_id[match.transaction_id] = match

    # Unmatched bank transactions for manual attachment
    unmatched_transactions = [t for t in transactions if t.id not in match_by_bank_id]
    
    # Build display data
    data = []
    index=1
    for txn in transactions:
        match = match_by_bank_id.get(txn.id)
        
        row = {
            'indice': index,
            'Date': txn.date.strftime('%d-%m-%Y'),
            'Amount': f"€{txn.amount:.2f}",
            'Description': txn.description or '',
            'Reference': txn.reference or '',
            'Receipt Type': txn.receipt_type or '',
            'Match Status': 'Unmatched',
            'Match Type': '',
            'Receipt': '',
            'Receipt Description': '',
            'to detach': False
        }
        
        if match:
            row['Match Status'] = 'Matched' if not match.is_conflict else 'Conflict'
            row['Match Type'] = match.match_type.value
            
            # Get receipt info
            if match.receipt_id:
                receipt = receipt_service.repository.get_by_id(match.receipt_id)
                if receipt:
                    receipt_name = Path(receipt.file_path).name if receipt.file_path else f"Receipt {receipt.id}"
                    row['Receipt'] = receipt_name
                    row['Receipt Description'] = receipt.description or ''
                    # If transaction has no receipt_type stored, show from matched receipt
                    if not row['Receipt Type']:
                        row['Receipt Type'] = receipt.receipt_type or ''

        # Status indicator for first column (non-editable)
        if row['Match Status'] == 'Matched':
            row['Status'] = '🟢'
        elif row['Match Status'] == 'Conflict':
            row['Status'] = '🟡'
        else:
            row['Status'] = '🔴'
        
        data.append(row)
        index += 1
    
    # Display tables
    import pandas as pd
    df = pd.DataFrame(data)
    # Use original transaction order as the DataFrame index
    if 'indice' in df.columns:
        df.set_index('indice', inplace=True)
        df.index.name = '#'

    # Split matched vs others so only matched show detach column
    matched_df = df[df['Match Status'] == 'Matched'].copy()
    other_df = df[df['Match Status'] != 'Matched'].copy()

    # Matched table with checkbox
    st.markdown("**Bank Transactions (Matched with detach)**")
    if not matched_df.empty:
        cols_order = ['Status', 'Date', 'Amount', 'Description', 'Reference', 'Receipt Type', 'Match Status', 'Match Type', 'Receipt', 'Receipt Description', 'to detach']
        matched_df = matched_df[cols_order]

        edited_df = st.data_editor(
            matched_df,
            width='stretch',
            height=300,
            hide_index=False,
            column_config={
                "Status": st.column_config.TextColumn(width="small", disabled=True),
                "to detach": st.column_config.CheckboxColumn(
                    "Detach",
                    help="Check to detach this receipt from transaction"
                ),
            },
            disabled=["Status", "Date", "Amount", "Description", "Reference", "Receipt Type", "Match Status", "Match Type", "Receipt", "Receipt Description"],
        )

        # Sync checkbox state from edited dataframe using the displayed index
        st.session_state.selected_detach = set()
        for df_idx, row in edited_df.iterrows():
            if row["to detach"]:
                # df_idx is 1-based index of the original transactions order
                txn_id = transactions[df_idx - 1].id
                st.session_state.selected_detach.add(txn_id)
    else:
        st.info("No matched transactions")

    # Other transactions without detach column
    st.markdown("**Other Bank Transactions (no detach)**")
    if not other_df.empty:
        cols_other = ['Status', 'Date', 'Amount', 'Description', 'Reference', 'Receipt Type', 'Match Status', 'Match Type', 'Receipt', 'Receipt Description']
        other_df = other_df[cols_other]

        def style_rows(row):
            if row['Match Status'] == 'Matched':
                color = '#d4edda'
            elif row['Match Status'] == 'Conflict':
                color = '#fff3cd'
            else:
                color = '#f8d7da'
            return [f'background-color: {color}'] * len(row)

        styled_other = other_df.style.apply(style_rows, axis=1)
        st.dataframe(styled_other, width='stretch', height=200, hide_index=False)
    else:
        st.info("No other transactions")

    st.markdown("---")
    
    # Batch detach button
    if st.session_state.selected_detach:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔓 Detach Selected Receipts", type="primary", width='stretch'):
                detach_count = 0
                for txn_id in st.session_state.selected_detach:
                    match = match_by_bank_id.get(txn_id)
                    if match and match.receipt_id:
                        # Remove match
                        matching_service.match_repo.delete_by_receipt_id(match.receipt_id)
                        # Clear bank transaction linkage
                        matching_service.bank_repo.update_match(txn_id, None)
                        matching_service.bank_repo.update_receipt_type(txn_id, None)
                        detach_count += 1
                
                if detach_count > 0:
                    # Recompute conflicts after all detaches
                    matching_service.recompute_conflict_flags()
                    st.success(f"✅ Detached {detach_count} receipt(s) from bank transactions")
                    st.session_state.selected_detach.clear()
                    st.rerun()
    else:
        st.caption("Select receipts above to enable batch detach")
    
    st.caption(f"📊 Total: {len(transactions)} transactions | "
               f"✅ Matched: {sum(1 for m in filtered_matches if m.transaction_id and not m.is_conflict)} | "
               f"⚠️ Conflicts: {sum(1 for m in filtered_matches if m.transaction_id and m.is_conflict)} | "
               f"❌ Unmatched: {len(transactions) - len(match_by_bank_id)}")
    
    st.divider()
    
    # Actions
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Reload from Excel"):
            try:
                config = st.session_state.config
                excel_path = config.paths.get('bank_excel')
                if excel_path and Path(excel_path).exists():
                    matching_service.bank_repo.clear_all()
                    count = matching_service.bank_repo.load_from_excel(excel_path)
                    st.success(f"Reloaded {count} transactions from Excel")
                    st.rerun()
                else:
                    st.error(f"Excel file not found: {excel_path}")
            except Exception as e:
                st.error(f"Failed to reload: {e}")
    
    with col2:
        if st.button("🔄 Recalculate All Matches"):
            with st.spinner("Recalculating matches..."):
                try:
                    count = matching_service.recalculate_all_matches()
                    st.success(f"✅ Successfully created {count} matches!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Recalculation failed: {e}")

    # Unmatched receipts simplified viewer
    st.divider()
    st.subheader("🧾 Unmatched Receipts")

    # Compute unmatched receipts (exclude ignored by default)
    try:
        # Get active period if exists
        period_repo = st.session_state.period_repo
        active_period = period_repo.get_active_processing_period()
        
        # Get receipts (filtered by active period if exists)
        if active_period:
            all_receipts = receipt_service.repository.get_by_period(active_period.id)
        else:
            all_receipts = receipt_service.repository.get_all()
        
        ignored_ids = st.session_state.ignored_repo.get_all_ignored_ids()
        unmatched_receipts = []
        for r in all_receipts:
            # Skip ignored receipts
            if r.id in ignored_ids:
                continue
            # Check if truly unmatched: no match record OR match exists but no transaction
            m = matching_service.match_repo.get_by_receipt_id(r.id)
            if m is None or m.transaction_id is None:
                unmatched_receipts.append(r)
            # Also include conflict receipts that haven't been accepted (still need assignment)
            elif m.is_conflict and not m.conflict_accepted:
                unmatched_receipts.append(r)
    except Exception as e:
        st.error(f"Failed to load unmatched receipts: {e}")
        unmatched_receipts = []

    if not unmatched_receipts:
        st.info("All receipts are matched or ignored.")
        return

    # Bound index
    if st.session_state.unmatched_index >= len(unmatched_receipts):
        st.session_state.unmatched_index = len(unmatched_receipts) - 1
    if st.session_state.unmatched_index < 0:
        st.session_state.unmatched_index = 0

    current_unmatched = unmatched_receipts[st.session_state.unmatched_index]
    current_match = matching_service.match_repo.get_by_receipt_id(current_unmatched.id)

    # Layout: simplified card with navigation
    col_left, col_right = st.columns([2, 1])

    with col_left:
        header_col, action_col = st.columns([3, 1])
        with header_col:
            st.markdown(f"**Receipt ({st.session_state.unmatched_index + 1}/{len(unmatched_receipts)})**")
        with action_col:
            # Detach if currently matched
            if current_match and current_match.transaction_id:
                if st.button("❌", key=f"detach_unmatched_{current_unmatched.id}", help="Detach from bank transaction"):
                    matching_service.match_repo.delete_by_receipt_id(current_unmatched.id)
                    matching_service.bank_repo.update_match(current_match.transaction_id, None)
                    matching_service.bank_repo.update_receipt_type(current_match.transaction_id, None)
                    matching_service.recompute_conflict_flags()
                    st.success("Receipt detached")
                    st.rerun()

        st.write(f"File: {Path(current_unmatched.file_path).name if current_unmatched.file_path else 'N/A'}")
        st.write(f"Type: {current_unmatched.receipt_type or 'Unknown'}")
        st.write(f"Date: {current_unmatched.date.strftime('%d-%m-%Y') if current_unmatched.date else 'N/A'}")
        st.write(f"Amount: €{current_unmatched.amount:.2f}" if current_unmatched.amount else "Amount: N/A")
        desc = current_unmatched.description or (current_unmatched.extracted_data.get('empresa') if current_unmatched.extracted_data else '') or ''
        if desc:
            st.write(f"Description: {desc}")
        
        # Show match info if exists
        if current_match and current_match.transaction_id:
            st.caption(f"⚠️ Currently matched to transaction #{current_match.transaction_id}")

        # Manual attach to unmatched bank transaction
        st.markdown("---")
        st.subheader("Manual Attach")
        if unmatched_transactions:
            option = st.selectbox(
                "Attach to bank transaction",
                options=[None] + unmatched_transactions,
                format_func=lambda t: "Select a transaction" if t is None else f"ID {t.id} | {t.date.strftime('%d-%m-%Y')} | €{t.amount:.2f} | {t.description or ''}",
                key=f"attach_txn_{current_unmatched.id}"
            )
            if st.button("🔗 Attach Receipt", key=f"attach_btn_{current_unmatched.id}", disabled=option is None):
                # Remove any existing match for this receipt
                if current_match:
                    matching_service.match_repo.delete_by_receipt_id(current_unmatched.id)
                    if current_match.transaction_id:
                        matching_service.bank_repo.update_match(current_match.transaction_id, None)
                        matching_service.bank_repo.update_receipt_type(current_match.transaction_id, None)

                if option is not None:
                    new_match = Match(
                        receipt_id=current_unmatched.id,
                        transaction_id=option.id,
                        match_type=MatchType.BOTH,
                        confidence=1.0,
                        is_conflict=False,
                    )
                    matching_service.match_repo.create(new_match)
                    matching_service.bank_repo.update_match(option.id, current_unmatched.id)
                    matching_service.bank_repo.update_receipt_type(option.id, current_unmatched.receipt_type)
                    matching_service.recompute_conflict_flags()
                    st.success(f"Attached to transaction {option.id}")
                    st.rerun()
        else:
            st.info("No unmatched bank transactions available")

    with col_right:
        nav1, nav2, nav3, nav4 = st.columns(4)
        with nav1:
            if st.button("⏮️ First", key="unmatched_first"):
                st.session_state.unmatched_index = 0
                st.rerun()
        with nav2:
            if st.button("◀️ Prev", key="unmatched_prev"):
                if st.session_state.unmatched_index > 0:
                    st.session_state.unmatched_index -= 1
                    st.rerun()
        with nav3:
            if st.button("▶️ Next", key="unmatched_next"):
                if st.session_state.unmatched_index < len(unmatched_receipts) - 1:
                    st.session_state.unmatched_index += 1
                    st.rerun()
        with nav4:
            if st.button("⏭️ Last", key="unmatched_last"):
                st.session_state.unmatched_index = len(unmatched_receipts) - 1
                st.rerun()

    # Optional: quick open in Receipts page
    open_col1, open_col2 = st.columns([1, 3])
    with open_col1:
        if st.button("📄 Open in Receipts", key="open_in_receipts"):
            st.session_state.navigate_to_receipt_id = current_unmatched.id
            # Queue page switch to apply before sidebar widget is created
            st.session_state.pending_nav_page = "Receipts"
            st.rerun()


def page_statistics():
    """Statistics page."""
    st.header("📊 Statistics")
    
    stats_service = st.session_state.stats_service
    period_repo = st.session_state.period_repo
    
    # Get active period if exists
    active_period = period_repo.get_active_processing_period()
    period_id = active_period.id if active_period else None
    
    # Get statistics (filtered by period if active)
    try:
        summary = stats_service.get_dashboard_summary(period_id)
    except Exception as e:
        st.error(f"Failed to load statistics: {e}")
        return
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    receipt_stats = summary.get('receipts', {})
    bank_stats = summary.get('bank', {})
    matching_stats = summary.get('matching', {})
    
    with col1:
        st.metric("Total Receipts", receipt_stats.get('total_count', 0))
    with col2:
        total_amount = receipt_stats.get('total_amount', 0)
        st.metric("Total Amount", f"€{total_amount:.2f}")
    with col3:
        # Total matches from matching stats
        matched_count = matching_stats.get('total_matches', 0)
        st.metric("Matched", matched_count)
    with col4:
        # Unmatched from bank stats
        unmatched_count = bank_stats.get('unmatched_count', 0)
        st.metric("Unmatched", unmatched_count)
    
    st.divider()
    
    # Additional metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Conflicts from matching stats
        conflict_count = matching_stats.get('conflicts', 0)
        st.metric("Conflicts", conflict_count)
    with col2:
        # Accepted conflicts from matching stats
        accepted_conflicts = matching_stats.get('accepted_conflicts', 0)
        st.metric("Conflicts Accepted", accepted_conflicts)
    with col3:
        # Ignored count from summary
        ignored_count = summary.get('ignored_count', 0)
        st.metric("Ignored", ignored_count)
    with col4:
        # Bank transactions total
        bank_count = bank_stats.get('total_transactions', 0)
        st.metric("Bank Transactions", bank_count)
    
    st.divider()
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Receipts by Type")
        
        type_breakdown = receipt_stats.get('by_type', {})
        if type_breakdown:
            import pandas as pd
            
            df_types = pd.DataFrame([
                {'Type': k, 'Count': v.get('count', 0), 'Amount': v.get('total_amount', 0)}
                for k, v in type_breakdown.items()
            ])
            
            # Sort by count descending
            df_types = df_types.sort_values('Count', ascending=False)
            
            # Simple bar chart using Streamlit's native chart
            st.bar_chart(df_types.set_index('Type')['Count'])
        else:
            st.info("No receipt type data available")
    
    with col2:
        st.subheader("Match Distribution")
        
        # Use match_type_breakdown from matching stats
        match_dist = matching_stats.get('match_type_breakdown', {})
        if match_dist:
            import pandas as pd
            
            df_matches = pd.DataFrame([
                {'Match Type': k, 'Count': v}
                for k, v in match_dist.items()
            ])
            
            # Create simple visualization
            st.bar_chart(df_matches.set_index('Match Type')['Count'])
        else:
            st.info("No match data available")
    
    st.divider()
    
    # Detailed table
    st.subheader("Detailed Breakdown by Type")
    
    type_breakdown = receipt_stats.get('by_type', {})
    if type_breakdown:
        import pandas as pd
        
        table_data = []
        for receipt_type, stats in type_breakdown.items():
            count = stats.get('count', 0)
            total = stats.get('total_amount', 0)
            avg = total / count if count > 0 else 0
            
            table_data.append({
                'Type': receipt_type,
                'Count': count,
                'Total Amount': f"€{total:.2f}",
                'Avg Amount': f"€{avg:.2f}"
            })
        
        df_table = pd.DataFrame(table_data)
        df_table = df_table.sort_values('Count', ascending=False)
        st.dataframe(df_table, width='stretch', hide_index=True)
    else:
        st.info("No detailed breakdown available")
    
    # Matching quality
    st.divider()
    st.subheader("Match Quality")
    
    avg_confidence = matching_stats.get('average_confidence', 0)
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Average Confidence", f"{avg_confidence:.1%}")
    
    with col2:
        match_rate = 0
        total_receipts = receipt_stats.get('total_count', 0)
        if total_receipts > 0:
            match_rate = matched_count / total_receipts
        st.metric("Match Rate", f"{match_rate:.1%}")
    
    # Recalculate matches button
    st.divider()
    st.subheader("⚙️ Matching Actions")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write("Recalculate all matches between receipts and bank transactions. This will clear existing matches and recreate them based on current data.")
    with col2:
        if st.button("🔄 Recalculate All Matches", type="primary"):
            with st.spinner("Recalculating matches..."):
                try:
                    matching_service = st.session_state.matching_service
                    count = matching_service.recalculate_all_matches()
                    st.success(f"✅ Successfully created {count} matches!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to recalculate matches: {e}")


def page_export():
    """Export page."""
    st.header("📤 Export Data")
    
    export_service = st.session_state.export_service
    
    st.write("Export receipts with bank matches for external reporting.")
    
    # Export format selector
    export_format = st.radio("Export Format", ['Excel (.xlsx)', 'CSV (.csv)'])
    
    # Export button
    if st.button("📥 Export All Data", type="primary"):
        with st.spinner("Exporting data..."):
            try:
                if export_format == 'Excel (.xlsx)':
                    file_path = export_service.export_receipts_with_matches_to_excel()
                else:
                    file_path = export_service.export_receipts_with_matches_to_csv()
                
                st.success(f"✅ Data exported successfully!")
                st.info(f"📁 File location: `{file_path}`")
                
                # Provide download button
                if Path(file_path).exists():
                    with open(file_path, 'rb') as f:
                        mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if export_format == 'Excel (.xlsx)' else 'text/csv'
                        st.download_button(
                            label="⬇️ Download File",
                            data=f.read(),
                            file_name=Path(file_path).name,
                            mime=mime_type
                        )
            except Exception as e:
                st.error(f"❌ Export failed: {e}")
    
    st.divider()
    
    # Export unmatched transactions
    st.subheader("Export Unmatched Bank Transactions")
    st.write("Export only bank transactions that have no matching receipt.")
    
    unmatched_format = st.radio("Format", ['Excel', 'CSV'], key='unmatched_format')
    
    if st.button("📥 Export Unmatched"):
        with st.spinner("Exporting unmatched transactions..."):
            try:
                file_path = export_service.export_unmatched_transactions(
                    format=unmatched_format.lower()
                )
                st.success(f"✅ Unmatched transactions exported!")
                st.info(f"📁 File location: `{file_path}`")
                
                # Provide download button
                if Path(file_path).exists():
                    with open(file_path, 'rb') as f:
                        mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if unmatched_format == 'Excel' else 'text/csv'
                        st.download_button(
                            label="⬇️ Download Unmatched File",
                            data=f.read(),
                            file_name=Path(file_path).name,
                            mime=mime_type,
                            key='download_unmatched'
                        )
            except Exception as e:
                st.error(f"❌ Export failed: {e}")
    
    st.divider()
    
    # Export all transactions complete
    st.subheader("📊 Export All Transactions (Complete)")
    st.write("Export all bank transactions with complete information including matched receipt details.")
    st.caption("Fields: id, Date/Fecha, Tipo, Expense, GL Account, Description/Descripcion, Amount/Importe, Local currency/Moneda local, Comments/Notas, Img. Filename/Nombre imagen")
    
    complete_format = st.radio("Format", ['Excel', 'CSV'], key='complete_format')
    
    if st.button("📥 Export All Transactions Complete"):
        with st.spinner("Exporting all transactions..."):
            try:
                file_path = export_service.export_all_transactions_complete(
                    format=complete_format.lower()
                )
                st.success(f"✅ All transactions exported!")
                st.info(f"📁 File location: `{file_path}`")
                
                # Provide download button
                if Path(file_path).exists():
                    with open(file_path, 'rb') as f:
                        mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if complete_format == 'Excel' else 'text/csv'
                        st.download_button(
                            label="⬇️ Download Complete Transactions File",
                            data=f.read(),
                            file_name=Path(file_path).name,
                            mime=mime_type,
                            key='download_complete'
                        )
            except Exception as e:
                st.error(f"❌ Export failed: {e}")


def get_database_stats():
    """Get database statistics."""
    config = st.session_state.config
    db = get_database(config.paths.get('database', './receipts.db'))
    
    stats = {
        'total_records': 0,
        'receipts_count': 0,
        'bank_transactions_count': 0,
        'matches_count': 0,
        'db_path': db.db_path,
        'db_size_mb': 0,
        'last_updated': None,
    }
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get counts
            cursor.execute("SELECT COUNT(*) as count FROM receipts")
            stats['receipts_count'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM bank_transactions")
            stats['bank_transactions_count'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM matches")
            stats['matches_count'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT MAX(updated_at) as last_update FROM receipts")
            result = cursor.fetchone()
            if result and result['last_update']:
                stats['last_updated'] = result['last_update']
            
            stats['total_records'] = (stats['receipts_count'] + 
                                     stats['bank_transactions_count'] + 
                                     stats['matches_count'])
        
        # Get file size
        if Path(stats['db_path']).exists():
            stats['db_size_mb'] = Path(stats['db_path']).stat().st_size / (1024 * 1024)
        
    except Exception as e:
        st.error(f"Error retrieving database stats: {e}")
    
    return stats


def get_last_backup_info():
    """Get information about the last backup."""
    config = st.session_state.config
    backup_dir = config.paths.get('backups', './backups')
    db_path = config.paths.get('database', './receipts.db')
    
    try:
        backup_manager = BackupManager(db_path, backup_dir)
        backups = backup_manager.list_backups()
        
        if backups:
            last_backup = backups[0]
            mtime = datetime.fromtimestamp(last_backup.stat().st_mtime)
            return {
                'path': str(last_backup),
                'time': mtime.strftime('%d-%m-%Y %H:%M:%S'),
                'size_mb': last_backup.stat().st_size / (1024 * 1024)
            }
    except Exception as e:
        st.warning(f"Could not retrieve backup info: {e}")
    
    return {'path': 'No backups found', 'time': 'N/A', 'size_mb': 0}


def reset_database():
    """Reset the database by deleting it."""
    config = st.session_state.config
    db_path = config.paths.get('database', './receipts.db')
    backup_dir = config.paths.get('backups', './backups')
    
    try:
        # Create emergency backup before reset
        if Path(db_path).exists():
            backup_manager = BackupManager(db_path, backup_dir)
            backup_manager.create_backup()
            Path(db_path).unlink()
        
        # Clear the cached database instance from the global module
        import src.core.database
        src.core.database._database = None
        
        st.success("✅ Database has been reset successfully! Emergency backup created.")
        
        # Reload the database and services - this will recreate the database and schema
        db = get_database(db_path)
        st.session_state.receipt_service = ReceiptService(config)
        st.session_state.matching_service = BankMatchingService(config)
        st.session_state.stats_service = StatisticsService(config)
        st.session_state.export_service = ExportService(config)
        st.session_state.ignored_repo = IgnoredRepository(db)
        st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to reset database: {e}")


def page_settings():
    """Settings page for configuration management."""
    st.header("⚙️ Configuration Settings")
    
    config = st.session_state.config
    
    st.markdown("""
    Configure the application settings below. Changes will be saved to `config.yaml`.
    """)
    
    # Create tabs for different configuration sections
    tabs = st.tabs(["📁 Paths", "🏦 Bank Matching", "📝 Receipt Types", "💾 Backup", "🔐 Admin"])
    
    # Tab 1: Paths Configuration
    with tabs[0]:
        st.subheader("File Paths")
        
        with st.form("paths_form"):
            bank_excel = st.text_input(
                "Bank Excel File",
                value=config.paths.get('bank_excel', ''),
                help="Path to the bank transactions Excel file"
            )
            
            input_dir = st.text_input(
                "Input Directory",
                value=config.paths.get('input_dir', './img'),
                help="Directory containing images to process"
            )
            
            # Note: output_dir is now determined dynamically by worker/period (./workers/{worker}/{period}/result)
            st.info("ℹ️ Output Directory is now automatically determined by the active worker and period: `./workers/{worker}/{period}/result`")
            
            exports_dir = st.text_input(
                "Exports Directory",
                value=config.paths.get('exports_dir', './exports'),
                help="Directory for exported files"
            )
            
            submit_paths = st.form_submit_button("💾 Save Paths")
            
            if submit_paths:
                config.set('paths.bank_excel', bank_excel)
                config.set('paths.input_dir', input_dir)
                # output_dir is no longer configurable
                config.set('paths.exports_dir', exports_dir)
                config.save()
                st.success("✅ Paths configuration saved!")
                st.rerun()
    
    # Tab 2: Bank Matching Configuration
    with tabs[1]:
        st.subheader("Bank Matching Settings")
        
        with st.form("matching_form"):
            amount_tolerance = st.number_input(
                "Amount Tolerance (€)",
                min_value=0.00,
                max_value=1.00,
                value=float(config.matching.get('amount_tolerance', 0.02)),
                step=0.01,
                format="%.2f",
                help="Tolerance for amount matching (e.g., 0.02 means ±2 cents)"
            )
            
            date_match_exact = st.checkbox(
                "Require Exact Date Match",
                value=config.matching.get('date_match_exact', True),
                help="If enabled, dates must match exactly. If disabled, allows ±1 day tolerance"
            )
            
            submit_matching = st.form_submit_button("💾 Save Matching Settings")
            
            if submit_matching:
                config.set('matching.amount_tolerance', amount_tolerance)
                config.set('matching.date_match_exact', date_match_exact)
                config.save()
                st.success("✅ Matching configuration saved!")
                st.rerun()
    
    # Tab 3: Receipt Types
    with tabs[2]:
        st.subheader("Receipt Type Categories")
        
        with st.form("receipt_types_form"):
            st.markdown("Enter receipt types (one per line):")
            
            current_types = config.receipt_types
            types_text = '\n'.join(current_types)
            
            receipt_types_input = st.text_area(
                "Receipt Types",
                value=types_text,
                height=200,
                help="Each line represents a receipt category"
            )
            
            submit_types = st.form_submit_button("💾 Save Receipt Types")
            
            if submit_types:
                # Parse types from text area
                new_types = [t.strip() for t in receipt_types_input.split('\n') if t.strip()]
                config.set('receipt_types', new_types)
                config.save()
                st.success(f"✅ Saved {len(new_types)} receipt types!")
                st.rerun()
        
        st.markdown("**Current types:**")
        st.write(", ".join(current_types))
    
    # Tab 4: Backup Configuration
    with tabs[3]:
        st.subheader("Backup Settings")
        
        with st.form("backup_form"):
            backup_enabled = st.checkbox(
                "Enable Automatic Backups",
                value=config.backup.get('enabled', True),
                help="Create automatic database backups"
            )
            
            retention_days = st.number_input(
                "Backup Retention (days)",
                min_value=1,
                max_value=90,
                value=config.backup.get('retention_days', 7),
                help="Number of days to keep backup files"
            )
            
            backup_on_startup = st.checkbox(
                "Backup on Startup",
                value=config.backup.get('backup_on_startup', True),
                help="Create a backup when the processor starts"
            )
            
            submit_backup = st.form_submit_button("💾 Save Backup Settings")
            
            if submit_backup:
                config.set('backup.enabled', backup_enabled)
                config.set('backup.retention_days', retention_days)
                config.set('backup.backup_on_startup', backup_on_startup)
                config.save()
                st.success("✅ Backup configuration saved!")
                st.rerun()
    
    # Tab 5: Admin Panel
    with tabs[4]:
        st.subheader("🔐 Admin Panel")
        
        st.markdown("**Database Information & Management**")
        
        # Get and display database statistics
        db_stats = get_database_stats()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 Total Records", db_stats['total_records'])
        with col2:
            st.metric("📋 Receipts", db_stats['receipts_count'])
        with col3:
            st.metric("🏦 Transactions", db_stats['bank_transactions_count'])
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("🔗 Matches", db_stats['matches_count'])
        with col2:
            st.metric("💾 DB Size", f"{db_stats['db_size_mb']:.2f} MB")
        
        # Database details
        st.markdown("**Database Details**")
        detail_col1, detail_col2 = st.columns(2)
        
        with detail_col1:
            st.text_input("Database Path", value=db_stats['db_path'], disabled=True)
            last_updated = db_stats['last_updated'] if db_stats['last_updated'] else "Never"
            st.text_input("Last Updated", value=last_updated, disabled=True)
        
        with detail_col2:
            backup_info = get_last_backup_info()
            st.text_input("Last Backup", value=backup_info['time'], disabled=True)
            st.text_input("Backup File Size", value=f"{backup_info['size_mb']:.2f} MB", disabled=True)
        
        # Admin operations
        st.markdown("**Database Operations**")
        
        col_ops1, col_ops2 = st.columns(2)
        
        with col_ops1:
            if st.button("🔄 Manual Backup Now", use_container_width=True):
                try:
                    backup_manager = BackupManager(
                        db_stats['db_path'],
                        config.paths.get('backups', './backups')
                    )
                    backup_path = backup_manager.create_backup()
                    if backup_path:
                        st.success(f"✅ Backup created: {backup_path}")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Backup failed: {e}")
        
        with col_ops2:
            if st.button("🗑️ Vacuum Database", use_container_width=True):
                try:
                    from src.core.database import Database
                    db = Database(db_stats['db_path'])
                    db.vacuum()
                    st.success("✅ Database optimized successfully")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Vacuum failed: {e}")
        
        # Dangerous operations
        st.markdown("**⚠️ Dangerous Operations**")
        st.warning(
            "The operations below are irreversible. An automatic backup will be created before resetting the database."
        )
        
        if st.button("🚨 Reset Database (Delete All Data)", use_container_width=True):
            st.session_state.show_reset_confirmation = True
        
        if st.session_state.get('show_reset_confirmation', False):
            st.markdown("### ⚠️ Confirm Database Reset")
            st.error(
                "This will **DELETE ALL DATA** in the database. "
                "An emergency backup will be created, but this action cannot be undone!"
            )
            
            confirm_col1, confirm_col2 = st.columns(2)
            
            with confirm_col1:
                if st.button("✅ Yes, Reset Database", use_container_width=True):
                    reset_database()
                    st.session_state.show_reset_confirmation = False
            
            with confirm_col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.show_reset_confirmation = False
    
    # Show current config file location
    st.divider()
    st.info(f"📄 Configuration file: `{config.config_path}`")
    
    # Advanced: View raw YAML
    with st.expander("🔧 View Raw Configuration"):
        import yaml
        with open(config.config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()
        st.code(config_yaml, language='yaml')


def main():
    """Main app entry point."""
    st.set_page_config(
        page_title="Receipt Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    # Setup logging before state init
    if 'logging_configured' not in st.session_state:
        config = get_config()
        setup_logging(config, app_name="dashboard", capture_std=False)
        st.session_state.logging_configured = True

    init_session_state()
    
    st.title("📊 Receipt Management Dashboard")
    
    # Apply any pending programmatic navigation before creating the sidebar widget
    if 'pending_nav_page' in st.session_state:
        st.session_state.nav_page = st.session_state.pending_nav_page
        del st.session_state.pending_nav_page

    # Show active period info in sidebar
    period_repo = st.session_state.period_repo
    active_period = period_repo.get_active_processing_period()
    if active_period:
        from src.repositories.worker_repository import WorkerRepository
        worker_repo = WorkerRepository(st.session_state.period_repo.db)
        worker = worker_repo.get_by_id(active_period.worker_id)
        worker_name = worker.nombre if worker else "Unknown"
        st.sidebar.info(f"📋 **Active Period:** {worker_name} - {active_period.month_year}")
    else:
        st.sidebar.info("📋 **No Active Period** (showing all data)")
    
    st.sidebar.divider()
    
    # Navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Receipts", "Bank Transactions", "Statistics", "Export", "⚙️ Settings"],
        key="nav_page"
    )
    
    if page == "Receipts":
        page_receipts()
    elif page == "Bank Transactions":
        page_bank_transactions()
    elif page == "Statistics":
        page_statistics()
    elif page == "Export":
        page_export()
    elif page == "⚙️ Settings":
        page_settings()


if __name__ == "__main__":
    main()
