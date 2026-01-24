# Admin Panel Features

## Overview
An comprehensive **Admin Panel** has been added to the Settings tab (⚙️ Configuration Settings) as the 5th tab labeled **🔐 Admin**.

## Location
- **Navigation**: Main Dashboard → ⚙️ Settings → 🔐 Admin tab

## Features

### 1. **Database Information & Management**

#### Database Metrics (displayed as cards)
- 📊 **Total Records**: Combined count of all database records
- 📋 **Receipts**: Number of receipts in the database
- 🏦 **Transactions**: Number of bank transactions
- 🔗 **Matches**: Number of matched records
- 💾 **DB Size**: Database file size in MB

#### Database Details (displayed in read-only fields)
- **Database Path**: Full path to the SQLite database file
- **Last Updated**: Timestamp of the last database modification
- **Last Backup**: Timestamp of the most recent backup
- **Backup File Size**: Size of the last backup in MB

### 2. **Database Operations**

#### Manual Backup
- **Button**: 🔄 Manual Backup Now
- **Function**: Creates an on-demand backup of the database
- **Result**: Shows confirmation with backup file path

#### Vacuum Database
- **Button**: 🗑️ Vacuum Database
- **Function**: Optimizes the database by reclaiming unused space
- **Result**: Shows confirmation after successful optimization

### 3. **Dangerous Operations** ⚠️

#### Reset Database
- **Button**: 🚨 Reset Database (Delete All Data)
- **Safety Features**:
  - Requires explicit confirmation before proceeding
  - Shows warning message about irreversible action
  - Automatically creates emergency backup before deletion
  - Two-step confirmation process:
    1. Click "Reset Database" to display confirmation dialog
    2. Click "Yes, Reset Database" to execute or "Cancel" to abort
- **Consequence**: Deletes all data in the database (emergency backup created)
- **Result**: Services are reloaded and app restarts after reset

## Implementation Details

### Helper Functions Added

1. **`get_database_stats()`**
   - Retrieves database statistics from all tables
   - Calculates database file size
   - Returns: dict with counts and metadata

2. **`get_last_backup_info()`**
   - Gets information about the most recent backup
   - Uses BackupManager to list available backups
   - Returns: dict with backup path, timestamp, and size

3. **`reset_database()`**
   - Creates emergency backup before deletion
   - Deletes the database file
   - Reloads all services
   - Triggers app refresh

### Database Access
- Uses SQLite queries to count records in:
  - `receipts` table
  - `bank_transactions` table
  - `matches` table
  - `ignored_receipts` table (for context)

### Backup Integration
- Leverages existing `BackupManager` class
- Backup files stored in configured backup directory
- Follows naming convention: `{db_name}_{YYYYMMDD_HHMMSS}.db`

## User Experience

### Visual Design
- Uses Streamlit columns for organized layout
- Color-coded metrics with icons
- Clear visual hierarchy
- Warning messages for dangerous operations
- Disabled input fields for read-only information

### Confirmation Dialogs
- Two-button confirmation for reset operation
- Error messages display if operations fail
- Success messages confirm operations completed
- Auto-refresh on successful operations

## Technical Integration

### Dependencies Used
- `streamlit` (st.metric, st.columns, st.button, etc.)
- `pathlib.Path` (file operations)
- `datetime` (timestamp formatting)
- `BackupManager` (existing module)
- `Database` (existing module)
- SQLite3 (via Database class)

### Session State
- Uses `st.session_state.show_reset_confirmation` for confirmation dialog
- Services are reloaded on reset to ensure clean state

## Configuration
All paths are read from `config.yaml`:
- `paths.database` - Database file location
- `paths.backups` - Backup directory location
